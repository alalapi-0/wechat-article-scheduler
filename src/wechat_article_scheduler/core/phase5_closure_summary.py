"""Phase5 收口摘要：聚合 round_103–106 预研 dry-run（只读）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.core.cross_project_calendar import build_publish_calendar_dry_run
from wechat_article_scheduler.core.multi_project_dry_run import build_multi_project_dry_run
from wechat_article_scheduler.core.ops_health_presearch import build_ops_health_dry_run
from wechat_article_scheduler.core.unified_outbox_presearch import build_unified_outbox_dry_run

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _presearch_root(config: AppConfig) -> Path:
    if (config.root / "config" / "projects.example.yaml").is_file():
        return config.root
    return _REPO_ROOT


def build_phase5_closure_summary(
    config: AppConfig,
) -> dict[str, Any]:
    root = _presearch_root(config)
    multi = build_multi_project_dry_run(root)
    calendar = build_publish_calendar_dry_run(root)
    outbox = build_unified_outbox_dry_run(root)
    ops = build_ops_health_dry_run(config)

    modules = {
        "round_103_multi_project": {
            "ok": multi.get("ok"),
            "project_count": multi.get("project_count"),
            "manifest_count": multi.get("manifest_count"),
        },
        "round_104_publish_calendar": {
            "ok": calendar.get("ok"),
            "event_count": calendar.get("event_count"),
            "conflict_count": calendar.get("conflict_count"),
        },
        "round_105_unified_outbox": {
            "ok": outbox.get("ok"),
            "package_count": outbox.get("outbox_index", {}).get("package_count"),
        },
        "round_106_ops_health": {
            "ok": ops.get("ok"),
            "checklist_count": len(ops.get("runbook_checklist") or []),
        },
    }
    all_ok = all(m.get("ok") for m in modules.values())

    return {
        "ok": all_ok,
        "phase": "phase5_closure",
        "mode": "dry_run",
        "agent_rounds": ["round_103", "round_104", "round_105", "round_106"],
        "modules": modules,
        "wechat_mainline": "微信公众号 scan/plan/run-once 仍为 P0；Phase5 均为预研",
        "docs": [
            "docs/phase5_multi_project_manifest.md",
            "docs/phase5_cross_project_calendar.md",
            "docs/phase5_unified_outbox.md",
            "docs/phase5_ops_maintenance.md",
            "docs/phase5_closure.md",
        ],
        "note": "Phase5 脚本轮收口摘要；不触发真实发布或 cron 安装。",
    }
