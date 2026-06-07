"""微信公众号闭环链路摘要（round_091 工作台辅助）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from wechat_article_scheduler.config import AppConfig


def build_wechat_chain_summary(config: AppConfig, conn: Any) -> dict[str, Any]:
    """基于 SQLite 汇总 scan/plan/run-once 相关计数与下一步建议（不联网）。"""
    article_rows = conn.execute(
        """
        SELECT status, COUNT(*) AS cnt FROM articles
        WHERE deleted_at IS NULL OR deleted_at = ''
        GROUP BY status
        """
    ).fetchall()
    job_rows = conn.execute(
        """
        SELECT status, COUNT(*) AS cnt FROM publish_jobs
        GROUP BY status
        """
    ).fetchall()
    imported = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM articles
        WHERE status IN ('imported', 'scheduled')
          AND (deleted_at IS NULL OR deleted_at = '')
        """
    ).fetchone()["cnt"]
    without_job = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM articles a
        WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
          AND a.status = 'imported'
          AND COALESCE(a.schedule_state, 'imported') = 'imported'
          AND NOT EXISTS (
            SELECT 1 FROM publish_jobs j
            WHERE j.article_id = a.id AND j.status IN ('pending', 'running')
          )
        """
    ).fetchone()["cnt"]
    due_now = conn.execute(
        """
        SELECT COUNT(*) AS cnt FROM publish_jobs
        WHERE status = 'pending'
          AND scheduled_at IS NOT NULL
          AND scheduled_at <= ?
        """,
        (datetime.now().isoformat(timespec="seconds"),),
    ).fetchone()["cnt"]
    failed = conn.execute(
        "SELECT COUNT(*) AS cnt FROM publish_jobs WHERE status = 'failed'"
    ).fetchone()["cnt"]

    article_counts = {str(r["status"]): int(r["cnt"]) for r in article_rows}
    job_counts = {str(r["status"]): int(r["cnt"]) for r in job_rows}

    next_action = "idle"
    next_cli: str | None = None
    if imported == 0 and sum(article_counts.values()) == 0:
        next_action = "scan"
        next_cli = "python -m wechat_article_scheduler.cli scan"
    elif without_job > 0:
        next_action = "plan"
        next_cli = "python -m wechat_article_scheduler.cli plan"
    elif due_now > 0:
        next_action = "run-once"
        next_cli = "python -m wechat_article_scheduler.cli run-once"
    elif failed > 0:
        next_action = "retry-failed"
        next_cli = "python -m wechat_article_scheduler.cli retry-failed"

    return {
        "wechat_mode": config.wechat_mode,
        "dry_run": config.dry_run,
        "article_counts": article_counts,
        "job_counts": job_counts,
        "imported_without_pending_job": without_job,
        "due_pending_jobs": due_now,
        "failed_jobs": failed,
        "recommended_next_action": next_action,
        "recommended_cli": next_cli,
        "chain_steps": ["scan", "plan", "run-once"],
        "safe_note": "默认 mock 不联网；真实 API 需 WECHAT_MODE=real 与用户凭证。",
    }
