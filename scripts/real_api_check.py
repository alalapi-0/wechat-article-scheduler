#!/usr/bin/env python3
"""真实微信 API 批量验证（只验证草稿创建，不执行最终发表）。

从环境变量 / .env 读取凭证，不打印 secret。报告写入 reports/real_api_runs/。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "fixtures" / "real_api_samples"
REPORTS_DIR = ROOT / "reports" / "real_api_runs"


def _load_dotenv() -> None:
    import os

    for name in (".env", ".env.local"):
        path = ROOT / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, parts[2].lstrip("\n")


def _load_sample(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    title = meta.get("title") or path.stem
    summary = meta.get("summary") or title[:120]
    return {"id": path.stem, "path": str(path.relative_to(ROOT)), "title": title, "summary": summary, "body": body}


def _quality_status(*, ok: bool, body: str, notes: list[str]) -> str:
    if not ok:
        if not body.strip():
            return "failed_empty_output"
        return "failed_parse_error"
    if notes:
        return "pass_with_issues"
    return "pass"


@dataclass
class SampleResult:
    sample_id: str
    title: str
    ok: bool
    media_id: str = ""
    error: str = ""
    content_len: int = 0
    rendered_len: int = 0
    rendered_preview: str = ""
    quality_notes: list[str] = field(default_factory=list)
    quality_status: str = ""


@dataclass
class CredentialStatus:
    wechat_mode: str = ""
    has_app_id: bool = False
    has_app_secret: bool = False
    ready: bool = False
    reason: str = ""


@dataclass
class RunReport:
    started_at: str
    provider: str = "wechat_official"
    model: str = "draft/add + material/thumb"
    wechat_mode: str = ""
    mock_used: bool = False
    samples_requested: int = 0
    success_count: int = 0
    failure_count: int = 0
    results: list[SampleResult] = field(default_factory=list)
    token_ok: bool = False
    blocking_reason: str = ""
    credentials: CredentialStatus = field(default_factory=CredentialStatus)
    dry_run: bool = False
    token_only: bool = False


def _quality_notes(title: str, body: str) -> list[str]:
    notes: list[str] = []
    if not body.strip():
        notes.append("正文为空")
    if title and body.lstrip().startswith("#"):
        first = body.lstrip().splitlines()[0].lstrip("#").strip()
        if first == title.strip():
            notes.append("正文首行与标题重复（创建草稿时会去重）")
    if "&lt;" in body:
        notes.append("疑似转义 HTML 源码")
    if len(body) > 20000:
        notes.append("正文过长，可能接近微信上限")
    return notes


def credential_status(cfg: Any) -> CredentialStatus:
    """检查是否具备真实 API 验证条件（不读取或打印 secret 值）。"""
    mode = (getattr(cfg, "wechat_mode", None) or "mock").strip().lower()
    has_id = bool((getattr(cfg, "wechat_app_id", None) or "").strip())
    has_secret = bool((getattr(cfg, "wechat_app_secret", None) or "").strip())
    status = CredentialStatus(
        wechat_mode=mode,
        has_app_id=has_id,
        has_app_secret=has_secret,
    )
    if mode != "real":
        status.reason = "WECHAT_MODE 不是 real"
        return status
    if not has_id or not has_secret:
        status.reason = "缺少 WECHAT_APP_ID / WECHAT_APP_SECRET"
        return status
    status.ready = True
    return status


def run_check(
    *,
    samples: int,
    dry_run: bool,
    token_only: bool,
) -> RunReport:
    _load_dotenv()
    sys.path.insert(0, str(ROOT / "src"))
    from wechat_article_scheduler.adapters import get_adapter
    from wechat_article_scheduler.config import load_config

    cfg = load_config()
    started = datetime.now(timezone.utc).isoformat()
    creds = credential_status(cfg)
    report = RunReport(
        started_at=started,
        wechat_mode=cfg.wechat_mode,
        mock_used=cfg.wechat_mode != "real",
        samples_requested=samples,
        credentials=creds,
        dry_run=dry_run,
        token_only=token_only,
    )

    if dry_run:
        report.blocking_reason = "DRY_RUN：仅验证本地配置，不调用微信 API"
        return report

    if not creds.ready:
        report.blocking_reason = (
            f"{creds.reason}，无法执行真实 API 验证"
            if creds.reason
            else "无法执行真实 API 验证"
        )
        return report
    adapter = get_adapter(cfg)
    try:
        adapter.get_access_token()
        report.token_ok = True
    except Exception as exc:  # noqa: BLE001
        report.blocking_reason = f"access_token 失败: {exc}"
        return report

    if token_only:
        return report

    paths = sorted(FIXTURES_DIR.glob("*.md"))[:samples]
    if not paths:
        report.blocking_reason = f"未找到样本：{FIXTURES_DIR}"
        return report

    for path in paths:
        sample = _load_sample(path)
        notes = _quality_notes(sample["title"], sample["body"])
        result = SampleResult(
            sample_id=sample["id"],
            title=sample["title"],
            ok=False,
            quality_notes=notes,
        )
        try:
            from wechat_article_scheduler.publish_preview import render_for_publish

            rendered = render_for_publish(sample["title"], sample["body"])
            result.rendered_len = len(rendered)
            result.rendered_preview = rendered[:240].replace("\n", " ")
            if not rendered.strip():
                notes.append("渲染后 HTML 为空")
            if "&lt;" in sample["body"] and "&lt;" in rendered:
                notes.append("渲染后仍含转义标签，预览可能异常")
            elif "&lt;" in sample["body"] and "&lt;" not in rendered:
                notes.append("转义 HTML 已归一化为可渲染段落")
            draft = adapter.create_draft(
                title=sample["title"],
                summary=sample["summary"],
                body=sample["body"],
                cover_path=str(cfg.wechat_default_thumb_path) if cfg.wechat_default_thumb_path else None,
            )
            result.media_id = draft.media_id[:16] + "..." if len(draft.media_id) > 16 else draft.media_id
            result.content_len = len(sample["body"])
            result.ok = True
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)[:500]
        result.quality_status = _quality_status(ok=result.ok, body=sample["body"], notes=notes)
        if result.ok:
            report.success_count += 1
        else:
            report.failure_count += 1
        report.results.append(result)

    return report


def _write_report(report: RunReport, *, reports_dir: Path | None = None) -> Path:
    output_dir = reports_dir or REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = output_dir / f"run_{stamp}"
    payload = asdict(report)
    base.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Real API Run Report",
        "",
        f"- started_at: {report.started_at}",
        f"- provider: {report.provider}",
        f"- wechat_mode: {report.wechat_mode}",
        f"- mock_used: {report.mock_used}",
        f"- token_ok: {report.token_ok}",
        f"- samples: {report.samples_requested}",
        f"- success: {report.success_count}",
        f"- failure: {report.failure_count}",
        "",
    ]
    if report.credentials.reason or not report.credentials.ready:
        lines.append(
            f"- credentials: mode={report.credentials.wechat_mode} "
            f"id={'yes' if report.credentials.has_app_id else 'no'} "
            f"secret={'yes' if report.credentials.has_app_secret else 'no'}"
        )
    if report.dry_run:
        lines.append("- dry_run: true")
    if report.token_only:
        lines.append("- token_only: true")
    if report.blocking_reason:
        lines.append(f"**blocking:** {report.blocking_reason}\n")
    for r in report.results:
        lines.append(f"## {r.sample_id} — {r.title}")
        lines.append(f"- ok: {r.ok}")
        if r.media_id:
            lines.append(f"- media_id: {r.media_id}")
        if r.error:
            lines.append(f"- error: {r.error}")
        if r.rendered_len:
            lines.append(f"- rendered_len: {r.rendered_len}")
        if r.rendered_preview:
            lines.append(f"- rendered_preview: {r.rendered_preview[:200]}...")
        if r.quality_status:
            lines.append(f"- quality_status: {r.quality_status}")
        if r.quality_notes:
            lines.append(f"- quality: {', '.join(r.quality_notes)}")
        lines.append("")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="真实微信 API 草稿创建验证（不提交发布）")
    parser.add_argument("--samples", type=int, default=3, help="草稿样本数量（默认 3）")
    parser.add_argument("--token-only", action="store_true", help="仅验证 access_token")
    parser.add_argument("--dry-run", action="store_true", help="仅检查本地配置，不调用微信 API")
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="报告输出目录（测试可指向临时目录）",
    )
    parser.add_argument(
        "--skip-if-blocked",
        action="store_true",
        help="无凭证或非 real 模式时仍写报告并以 0 退出（Agent/CI 用，不硬停整轮）",
    )
    args = parser.parse_args()

    report = run_check(
        samples=max(1, args.samples),
        dry_run=args.dry_run,
        token_only=args.token_only,
    )
    out = _write_report(report, reports_dir=args.report_dir)
    print(f"report: {out.with_suffix('.json')}")
    print(f"mode={report.wechat_mode} mock={report.mock_used} token_ok={report.token_ok}")
    print(f"success={report.success_count} failure={report.failure_count}")
    if report.wechat_mode == "real" and report.success_count > 0:
        print(
            "cleanup: 真实草稿-only 测试会在公众号后台留下草稿；"
            "测试后请登录后台手动删除测试草稿，并对照工作台「微信草稿」区的 media_id 核对"
        )
    if report.blocking_reason:
        print(f"blocking: {report.blocking_reason}", file=sys.stderr)
    blocked = bool(report.blocking_reason) and not report.token_ok
    if args.skip_if_blocked and (report.mock_used or blocked):
        return 0
    if report.mock_used or (blocked and not args.token_only and not args.dry_run):
        return 2
    if report.failure_count > 0:
        return 1
    if report.blocking_reason and not args.token_only and not args.dry_run:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
