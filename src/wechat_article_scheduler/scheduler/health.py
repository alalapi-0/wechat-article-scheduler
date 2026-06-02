"""调度器健康检查（Round 14 / round_069）。"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler.policies import max_retries_for


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def build_scheduler_health(config: AppConfig) -> dict[str, Any]:
    timeout = max(60, int(getattr(config, "scheduler_claim_timeout_seconds", 900)))
    max_retries = max_retries_for(config)
    with db.connect(config.database_path) as conn:
        pending = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM publish_jobs WHERE status = 'pending'"
            ).fetchone()["c"]
        )
        pending_due = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM publish_jobs j
                JOIN articles a ON a.id = j.article_id
                WHERE j.status = 'pending'
                  AND j.scheduled_at <= datetime('now')
                  AND (j.next_retry_at IS NULL OR j.next_retry_at <= datetime('now'))
                  AND (a.deleted_at IS NULL OR a.deleted_at = '')
                """
            ).fetchone()["c"]
        )
        running = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM publish_jobs WHERE status = 'running'"
            ).fetchone()["c"]
        )
        failed = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM publish_jobs WHERE status = 'failed'"
            ).fetchone()["c"]
        )
        retry_waiting = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM publish_jobs
                WHERE status = 'pending'
                  AND next_retry_at IS NOT NULL
                  AND next_retry_at > datetime('now')
                """
            ).fetchone()["c"]
        )
        stale_running = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c FROM publish_jobs
                WHERE status = 'running'
                  AND datetime(updated_at) <= datetime('now', ?)
                """,
                (f"-{timeout} seconds",),
            ).fetchone()["c"]
        )
        lock_info: dict[str, Any] | None = None
        if _table_exists(conn, "scheduler_locks"):
            lock_row = conn.execute(
                "SELECT owner, acquired_at, expires_at FROM scheduler_locks WHERE lock_name = 'run_once'"
            ).fetchone()
            if lock_row:
                lock_info = {
                    "holder": lock_row["owner"],
                    "acquired_at": lock_row["acquired_at"],
                    "expires_at": lock_row["expires_at"],
                }
        ok = stale_running == 0
        summary = (
            f"待发布 {pending}（到点 {pending_due}），发布中 {running}，"
            f"失败 {failed}，退避等待 {retry_waiting}"
        )
        if stale_running:
            summary += f"；卡住 {stale_running} 条 running 需恢复"
        return {
            "ok": ok,
            "summary": summary,
            "wechat_mode": config.wechat_mode,
            "dry_run": config.dry_run,
            "max_job_retries": max_retries,
            "claim_timeout_seconds": timeout,
            "counts": {
                "pending": pending,
                "pending_due": pending_due,
                "running": running,
                "failed": failed,
                "retry_waiting": retry_waiting,
                "stale_running": stale_running,
            },
            "lock": lock_info,
        }


def print_scheduler_health(config: AppConfig) -> None:
    payload = build_scheduler_health(config)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
