#!/usr/bin/env python3
"""真实微信 API 批量验证（默认 draft-only，不提交 freepublish）。

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


def _redact_response(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: ("***" if k in ("access_token", "secret") else _redact_response(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_redact_response(x) for x in data]
    return data


@dataclass
class SampleResult:
    sample_id: str
    title: str
    ok: bool
    media_id: str = ""
    error: str = ""
    content_len: int = 0
    quality_notes: list[str] = field(default_factory=list)


@dataclass
class RunReport:
    started_at: str
    provider: str = "wechat_official"
    model: str = "draft/add + material/thumb"
    wechat_mode: str = ""
    enable_publish: bool = False
    mock_used: bool = False
    samples_requested: int = 0
    success_count: int = 0
    failure_count: int = 0
    results: list[SampleResult] = field(default_factory=list)
    token_ok: bool = False
    blocking_reason: str = ""


def _quality_notes(title: str, body: str) -> list[str]:
    notes: list[str] = []
    if not body.strip():
        notes.append("正文为空")
    if title and body.lstrip().startswith("#"):
        first = body.lstrip().splitlines()[0].lstrip("#").strip()
        if first == title.strip():
            notes.append("正文首行与标题重复（发布时会去重）")
    if "&lt;" in body:
        notes.append("疑似转义 HTML 源码")
    if len(body) > 20000:
        notes.append("正文过长，可能接近微信上限")
    return notes


def run_check(*, samples: int, dry_run: bool, token_only: bool) -> RunReport:
    _load_dotenv()
    sys.path.insert(0, str(ROOT / "src"))
    from wechat_article_scheduler.adapters import get_adapter
    from wechat_article_scheduler.config import load_config

    cfg = load_config()
    started = datetime.now(timezone.utc).isoformat()
    report = RunReport(
        started_at=started,
        wechat_mode=cfg.wechat_mode,
        enable_publish=bool(cfg.wechat_enable_publish),
        mock_used=cfg.wechat_mode != "real",
        samples_requested=samples,
    )

    if cfg.wechat_mode != "real":
        report.blocking_reason = "WECHAT_MODE 不是 real，无法执行真实 API 验证"
        return report
    if not cfg.wechat_app_id or not cfg.wechat_app_secret:
        report.blocking_reason = "缺少 WECHAT_APP_ID / WECHAT_APP_SECRET"
        return report
    if cfg.wechat_enable_publish:
        report.blocking_reason = (
            "WECHAT_ENABLE_PUBLISH=true：为安全起见请设为 false 后再运行本脚本"
        )
        return report

    adapter = get_adapter(cfg)
    try:
        adapter.get_access_token()
        report.token_ok = True
    except Exception as exc:  # noqa: BLE001
        report.blocking_reason = f"access_token 失败: {exc}"
        return report

    if token_only or dry_run:
        if dry_run:
            report.blocking_reason = "DRY_RUN：仅验证配置与 token"
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
            draft = adapter.create_draft(
                title=sample["title"],
                summary=sample["summary"],
                body=sample["body"],
                cover_path=str(cfg.wechat_default_thumb_path) if cfg.wechat_default_thumb_path else None,
            )
            result.media_id = draft.media_id[:16] + "..." if len(draft.media_id) > 16 else draft.media_id
            result.content_len = len(sample["body"])
            submit = adapter.submit_publish(draft.media_id)
            if submit.get("skipped"):
                result.ok = True
            else:
                result.ok = False
                result.error = "意外提交了发布（应被 WECHAT_ENABLE_PUBLISH=false 跳过）"
        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)[:500]
        if result.ok:
            report.success_count += 1
        else:
            report.failure_count += 1
        report.results.append(result)

    return report


def _write_report(report: RunReport) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = REPORTS_DIR / f"run_{stamp}"
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
        f"- enable_publish: {report.enable_publish}",
        f"- token_ok: {report.token_ok}",
        f"- samples: {report.samples_requested}",
        f"- success: {report.success_count}",
        f"- failure: {report.failure_count}",
        "",
    ]
    if report.blocking_reason:
        lines.append(f"**blocking:** {report.blocking_reason}\n")
    for r in report.results:
        lines.append(f"## {r.sample_id} — {r.title}")
        lines.append(f"- ok: {r.ok}")
        if r.media_id:
            lines.append(f"- media_id: {r.media_id}")
        if r.error:
            lines.append(f"- error: {r.error}")
        if r.quality_notes:
            lines.append(f"- quality: {', '.join(r.quality_notes)}")
        lines.append("")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="真实微信 API 闭环验证（draft-only）")
    parser.add_argument("--samples", type=int, default=3, help="草稿样本数量（默认 3）")
    parser.add_argument("--token-only", action="store_true", help="仅验证 access_token")
    parser.add_argument("--dry-run", action="store_true", help="不调用 draft/add")
    args = parser.parse_args()

    report = run_check(samples=max(1, args.samples), dry_run=args.dry_run, token_only=args.token_only)
    out = _write_report(report)
    print(f"report: {out.with_suffix('.json')}")
    print(f"mode={report.wechat_mode} mock={report.mock_used} token_ok={report.token_ok}")
    print(f"success={report.success_count} failure={report.failure_count}")
    if report.blocking_reason:
        print(f"blocking: {report.blocking_reason}", file=sys.stderr)
    if report.mock_used or not report.token_ok:
        return 2
    if report.failure_count > 0:
        return 1
    if report.blocking_reason and not args.token_only and not args.dry_run:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
