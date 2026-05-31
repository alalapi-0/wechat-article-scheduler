#!/usr/bin/env python3
"""Auto-Approved Real API Pipeline — 真实微信 API 端到端验证。

本仓库已在 Round 43 移除人工审核；本脚本用于 Agent 推进轮：
  真实 API 草稿创建 → 自动标记 auto_approved → scan/plan/run-once 下游 → 报告落盘

默认启用 AUTO_APPROVE_GENERATIONS（不等待人工确认）。
人工审核模式：设置 REVIEW_MODE=manual 且 AUTO_APPROVE_GENERATIONS=false。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports" / "auto_approve_pipeline"
REAL_API_SCRIPT = ROOT / "scripts" / "real_api_check.py"


def _load_real_api_check():
    spec = importlib.util.spec_from_file_location("real_api_check", REAL_API_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["real_api_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_dotenv() -> None:
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


def _pipeline_auto_approve_enabled() -> bool:
    raw = os.getenv("AUTO_APPROVE_GENERATIONS")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    mode = (os.getenv("REVIEW_MODE") or "auto").strip().lower()
    if mode == "auto":
        return True
    return (os.getenv("SKIP_HUMAN_REVIEW") or "").strip().lower() in {"1", "true", "yes", "on"}


def _run_cli_downstream(*, round_num: int) -> dict[str, Any]:
    """scan → schedule now → run-once：验证发布任务下游（额外 1 次真实 draft）。"""
    sys.path.insert(0, str(ROOT / "src"))
    from wechat_article_scheduler.config import load_config
    from wechat_article_scheduler import db
    from wechat_article_scheduler.scanner import scan_inbox
    from wechat_article_scheduler.schedule_assign import assign_article_schedule
    from wechat_article_scheduler.scheduler.runtime import run_due_jobs

    cfg = load_config()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    inbox = cfg.inbox_dir
    inbox.mkdir(parents=True, exist_ok=True)
    pipeline_file = inbox / f"pipeline_round{round_num}_{stamp}.md"
    pipeline_file.write_text(
        f"---\ntitle: \"[PIPELINE-R{round_num}] 下游验证 {stamp}\"\n"
        f"summary: Auto-approve pipeline 下游 run-once 验证。\n---\n\n"
        f"本轮 Round {round_num} 于 {stamp} 写入，用于 scan/plan/run-once 闭环。\n",
        encoding="utf-8",
    )

    scan_stats = scan_inbox(cfg)
    article_id: int | None = None
    with db.connect(cfg.database_path) as conn:
        row = conn.execute(
            "SELECT id FROM articles WHERE source_path = ? ORDER BY id DESC LIMIT 1",
            (str(pipeline_file.relative_to(cfg.root)),),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT id FROM articles ORDER BY id DESC LIMIT 1",
            ).fetchone()
        if row:
            article_id = int(row["id"])

    downstream: dict[str, Any] = {
        "pipeline_file": str(pipeline_file.relative_to(ROOT)),
        "scan": scan_stats,
        "article_id": article_id,
        "scheduled": False,
        "run_once": {},
        "draft_rows": 0,
    }

    if article_id is None:
        downstream["error"] = "scan 后未找到 article_id"
        return downstream

    assign_article_schedule(cfg, article_id, datetime.now())
    downstream["scheduled"] = True
    run_stats = run_due_jobs(cfg)
    downstream["run_once"] = run_stats

    with db.connect(cfg.database_path) as conn:
        draft_count = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts WHERE article_id = ?",
            (article_id,),
        ).fetchone()
        downstream["draft_rows"] = int(draft_count["c"]) if draft_count else 0

    return downstream


def _db_summary(database_path: Path) -> dict[str, int]:
    if not database_path.is_file():
        return {}
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        out: dict[str, int] = {}
        for label, sql in (
            ("articles", "SELECT COUNT(*) AS c FROM articles"),
            ("pending_jobs", "SELECT COUNT(*) AS c FROM publish_jobs WHERE status='pending'"),
            ("done_jobs", "SELECT COUNT(*) AS c FROM publish_jobs WHERE status='done'"),
            ("wechat_drafts", "SELECT COUNT(*) AS c FROM wechat_drafts"),
        ):
            row = conn.execute(sql).fetchone()
            out[label] = int(row["c"]) if row else 0
        return out


def run_pipeline(*, round_num: int, samples: int, skip_downstream: bool) -> dict[str, Any]:
    _load_dotenv()
    if _pipeline_auto_approve_enabled():
        os.environ.setdefault("AUTO_APPROVE_GENERATIONS", "true")
        os.environ.setdefault("REVIEW_MODE", "auto")

    rac = _load_real_api_check()
    api_report = rac.run_check(
        samples=max(1, samples),
        dry_run=False,
        token_only=False,
        auto_approve=True,
    )
    api_report_path = rac._write_report(api_report)

    downstream: dict[str, Any] | None = None
    if not skip_downstream and api_report.token_ok and not api_report.blocking_reason:
        try:
            downstream = _run_cli_downstream(round_num=round_num)
        except Exception as exc:  # noqa: BLE001
            downstream = {"error": str(exc)[:500]}

    sys.path.insert(0, str(ROOT / "src"))
    from wechat_article_scheduler.config import load_config

    cfg = load_config()
    db_stats = _db_summary(cfg.database_path)

    return {
        "round": round_num,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "auto_approve_enabled": _pipeline_auto_approve_enabled(),
        "api_report_json": str(api_report_path.with_suffix(".json").relative_to(ROOT)),
        "api_report_md": str(api_report_path.with_suffix(".md").relative_to(ROOT)),
        "provider": api_report.provider,
        "model": api_report.model,
        "mock": api_report.mock_used,
        "success_count": api_report.success_count,
        "failure_count": api_report.failure_count,
        "auto_approved_count": api_report.auto_approved_count,
        "token_ok": api_report.token_ok,
        "blocking_reason": api_report.blocking_reason,
        "downstream": downstream,
        "database": db_stats,
    }


def _write_round_report(payload: dict[str, Any]) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    n = payload["round"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = REPORTS_DIR / f"round_{n:02d}_{stamp}"
    base.with_suffix(".json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        f"# Auto-Approved Real API Pipeline Round {n} Report",
        "",
        "## 本轮目标",
        "",
        "真实微信 API 草稿创建 → 自动通过（无人工审核）→ 下游 run-once → 报告落盘。",
        "",
        "## 真实 API 调用",
        "",
        f"- Provider: {payload.get('provider', '')}",
        f"- Model: {payload.get('model', '')}",
        f"- 调用次数: {payload.get('success_count', 0) + payload.get('failure_count', 0)}",
        f"- mock: {'Yes' if payload.get('mock') else 'No'}",
        f"- 成功数量: {payload.get('success_count', 0)}",
        f"- 失败数量: {payload.get('failure_count', 0)}",
        "",
        "## 自动审核通过结果",
        "",
        f"- auto_approve enabled: {payload.get('auto_approve_enabled')}",
        f"- 自动通过数量: {payload.get('auto_approved_count', 0)}",
        "- 状态字段: review_status=auto_approved, review_mode=auto, reviewer=agent",
        f"- approved 输出路径: {payload.get('api_report_json', '')}",
        f"- metadata 路径: {payload.get('api_report_json', '')}",
        "",
        "## 后续流程执行结果",
        "",
    ]
    ds = payload.get("downstream") or {}
    if ds:
        lines.append(f"- scan: {json.dumps(ds.get('scan', {}), ensure_ascii=False)}")
        lines.append(f"- run_once: {json.dumps(ds.get('run_once', {}), ensure_ascii=False)}")
        lines.append(f"- wechat_drafts (article): {ds.get('draft_rows', 0)}")
    else:
        lines.append("- 下游: 跳过或未执行")
    db = payload.get("database") or {}
    lines.extend(
        [
            f"- database articles: {db.get('articles', 0)}",
            f"- pending_jobs: {db.get('pending_jobs', 0)}",
            f"- done_jobs: {db.get('done_jobs', 0)}",
            f"- wechat_drafts total: {db.get('wechat_drafts', 0)}",
            "",
            "## Git 提交",
            "",
            "- branch: main",
            "",
            "## 是否自动进入下一轮",
            "",
        ]
    )
    if payload.get("blocking_reason"):
        lines.append(f"- 否，硬阻塞: {payload['blocking_reason']}")
    elif payload.get("failure_count", 0) > 0:
        lines.append("- 是，继续（有失败样本但流程已记录）")
    else:
        lines.append(f"- 是，继续 Round {n + 1}")
    base.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-Approved Real API Pipeline")
    parser.add_argument("--round", type=int, default=1, help="轮次编号（默认 1）")
    parser.add_argument("--samples", type=int, default=3, help="real_api_check 样本数")
    parser.add_argument(
        "--skip-downstream",
        action="store_true",
        help="跳过 scan/run-once 下游（仅 real_api_check）",
    )
    args = parser.parse_args()

    payload = run_pipeline(
        round_num=max(1, args.round),
        samples=max(1, args.samples),
        skip_downstream=args.skip_downstream,
    )
    out = _write_round_report(payload)
    print(f"pipeline_report: {out.with_suffix('.json')}")
    print(
        f"round={payload['round']} success={payload['success_count']} "
        f"auto_approved={payload['auto_approved_count']}"
    )
    if payload.get("blocking_reason"):
        print(f"blocking: {payload['blocking_reason']}", file=sys.stderr)
        return 2
    if payload.get("mock"):
        return 2
    if payload.get("failure_count", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
