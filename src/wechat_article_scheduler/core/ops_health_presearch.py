"""Phase5 长期运维预研：runbook 检查清单 + 健康指标聚合 dry-run（不改 cron）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.core.unified_outbox_presearch import index_outbox_directories
from wechat_article_scheduler.scheduler.health import build_scheduler_health

_REPO_ROOT = Path(__file__).resolve().parents[3]

DEPLOY_EXAMPLE_PATHS = (
    "deploy/examples/scheduler/cron-run-once.example",
    "deploy/examples/scheduler/com.wechat-article-scheduler.plist.example",
    "deploy/examples/scheduler/wechat-article-scheduler.service.example",
    "docs/scheduler_runbook.md",
)


def default_ops_config_path(root: Path) -> Path:
    custom = root / "config" / "ops_maintenance.yaml"
    if custom.exists():
        return custom
    example = root / "config" / "ops_maintenance.example.yaml"
    if example.exists():
        return example
    return _REPO_ROOT / "config" / "ops_maintenance.example.yaml"


def load_ops_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "runbook_checklist": [], "guardrails": []}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _auto_check(
    check_id: str,
    config: AppConfig,
    *,
    scheduler_payload: dict[str, Any],
) -> tuple[str, bool, str]:
    if check_id == "database_exists":
        exists = config.database_path.is_file()
        return ("pass" if exists else "fail", exists, str(config.database_path))
    if check_id == "scheduler_ok":
        ok = bool(scheduler_payload.get("ok"))
        return ("pass" if ok else "warn", ok, str(scheduler_payload.get("summary", "")))
    if check_id == "inbox_readable":
        ok = config.inbox_dir.is_dir()
        return ("pass" if ok else "fail", ok, str(config.inbox_dir))
    if check_id == "log_policy":
        configured = config.log_file is not None
        if configured:
            exists = config.log_file.is_file() if config.log_file else False
            status = "pass" if exists else "warn"
            return (status, True, f"log_file={config.log_file} exists={exists}")
        return ("pass", True, "未配置 log_file（允许）")
    if check_id == "deploy_examples_present":
        root = _REPO_ROOT if (_REPO_ROOT / DEPLOY_EXAMPLE_PATHS[0]).is_file() else config.root
        missing = [p for p in DEPLOY_EXAMPLE_PATHS if not (root / p).is_file()]
        ok = not missing
        detail = "全部样例在仓" if ok else f"缺失: {', '.join(missing)}"
        return ("pass" if ok else "warn", ok, detail)
    if check_id == "manual_only":
        return ("manual", True, "须按 runbook 人工执行")
    return ("unknown", False, f"未知 auto_check: {check_id}")


def evaluate_runbook_checklist(
    config: AppConfig,
    ops_cfg: dict[str, Any],
    *,
    scheduler_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw in ops_cfg.get("runbook_checklist") or []:
        if not isinstance(raw, dict):
            continue
        check_id = str(raw.get("auto_check") or "")
        status, ok, detail = _auto_check(check_id, config, scheduler_payload=scheduler_payload)
        items.append(
            {
                "id": raw.get("id"),
                "title": raw.get("title"),
                "cadence": raw.get("cadence"),
                "auto_check": check_id,
                "status": status,
                "ok": ok,
                "detail": detail,
            }
        )
    return items


def _article_counts(config: AppConfig) -> dict[str, int]:
    with db.connect(config.database_path) as conn:
        imported = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM articles WHERE status = 'imported' "
                "AND (deleted_at IS NULL OR deleted_at = '')"
            ).fetchone()["c"]
        )
        jobs_pending = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM publish_jobs WHERE status = 'pending'"
            ).fetchone()["c"]
        )
    inbox_files = 0
    if config.inbox_dir.is_dir():
        inbox_files = sum(1 for p in config.inbox_dir.iterdir() if p.is_file())
    return {
        "imported_articles": imported,
        "pending_jobs": jobs_pending,
        "inbox_files": inbox_files,
    }


def build_ops_health_dry_run(config: AppConfig) -> dict[str, Any]:
    root = config.root
    cfg_path = default_ops_config_path(root)
    ops_cfg = load_ops_config(cfg_path)
    scheduler = build_scheduler_health(config)
    checklist = evaluate_runbook_checklist(config, ops_cfg, scheduler_payload=scheduler)
    outbox_idx = index_outbox_directories(root, scan_roots=["outbox"])
    db_size = config.database_path.stat().st_size if config.database_path.is_file() else 0

    auto_items = [c for c in checklist if c.get("auto_check") != "manual_only"]
    auto_ok = all(c.get("ok") for c in auto_items if c.get("status") != "unknown")
    hard_fail = any(c.get("status") == "fail" for c in checklist)

    return {
        "ok": scheduler.get("ok", True) and auto_ok and not hard_fail,
        "phase": "phase5_ops_maintenance",
        "mode": "dry_run",
        "config_path": str(cfg_path.resolve()),
        "guardrails": ops_cfg.get("guardrails")
        or ["不修改生产 cron", "备份须人工执行"],
        "wechat_mode": config.wechat_mode,
        "metrics": {
            "database": {
                "path": str(config.database_path),
                "size_bytes": db_size,
                "exists": config.database_path.is_file(),
            },
            "articles": _article_counts(config),
            "scheduler": scheduler,
            "outbox": {
                "package_count": outbox_idx.get("package_count", 0),
                "platform_count": outbox_idx.get("platform_count", 0),
            },
            "logging": {
                "log_file": str(config.log_file) if config.log_file else None,
                "log_level": config.log_level,
            },
        },
        "runbook_checklist": checklist,
        "deploy_examples_in_repo": [
            {"path": p, "present": (root / p).is_file()} for p in DEPLOY_EXAMPLE_PATHS
        ],
        "wechat_mainline": "scan/plan/run-once 未因本模块改变",
        "note": "运维预研聚合；不安装 cron、不写 launchd。",
    }
