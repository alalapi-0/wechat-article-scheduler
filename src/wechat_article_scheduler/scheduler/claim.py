"""调度 claim、单实例锁与卡住任务恢复（Round 14 / round_069）。"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timedelta

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.scheduler.policies import max_retries_for, retry_backoff_seconds

logger = logging.getLogger(__name__)

RUN_ONCE_LOCK = "run_once"


def new_claim_token() -> str:
    return uuid.uuid4().hex


def try_claim_job(conn: sqlite3.Connection, job_id: int, token: str) -> bool:
    """原子抢占：仅 pending 可进入 running。"""
    cur = conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'running',
            claim_token = ?,
            claimed_at = datetime('now'),
            updated_at = datetime('now')
        WHERE id = ? AND status = 'pending'
        """,
        (token, int(job_id)),
    )
    return cur.rowcount == 1


def clear_job_claim(conn: sqlite3.Connection, job_id: int) -> None:
    conn.execute(
        """
        UPDATE publish_jobs
        SET claim_token = NULL, claimed_at = NULL, updated_at = datetime('now')
        WHERE id = ?
        """,
        (int(job_id),),
    )


def acquire_run_lock(conn: sqlite3.Connection, config: AppConfig) -> tuple[bool, str | None]:
    """获取 run-once / scheduler 单实例锁；返回 (成功, 当前持有者)。"""
    owner = f"pid-{os.getpid()}"
    ttl = max(30, int(getattr(config, "scheduler_lock_ttl_seconds", 300)))
    expires = (datetime.now() + timedelta(seconds=ttl)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "DELETE FROM scheduler_locks WHERE lock_name = ? AND expires_at < datetime('now')",
        (RUN_ONCE_LOCK,),
    )
    row = conn.execute(
        "SELECT owner, expires_at FROM scheduler_locks WHERE lock_name = ?",
        (RUN_ONCE_LOCK,),
    ).fetchone()
    if row is not None:
        if row["owner"] == owner:
            conn.execute(
                "UPDATE scheduler_locks SET expires_at = ?, acquired_at = datetime('now') WHERE lock_name = ?",
                (expires, RUN_ONCE_LOCK),
            )
            return True, None
        return False, str(row["owner"])
    conn.execute(
        """
        INSERT INTO scheduler_locks (lock_name, owner, expires_at)
        VALUES (?, ?, ?)
        """,
        (RUN_ONCE_LOCK, owner, expires),
    )
    return True, None


def release_run_lock(conn: sqlite3.Connection, config: AppConfig) -> None:
    owner = f"pid-{os.getpid()}"
    conn.execute(
        "DELETE FROM scheduler_locks WHERE lock_name = ? AND owner = ?",
        (RUN_ONCE_LOCK, owner),
    )


def recover_stale_running_jobs(conn: sqlite3.Connection, config: AppConfig) -> int:
    """将超时仍停留在 running 的任务恢复为 pending，避免卡死。"""
    timeout = max(60, int(getattr(config, "scheduler_claim_timeout_seconds", 900)))
    rows = conn.execute(
        """
        SELECT id, article_id, retry_count
        FROM publish_jobs
        WHERE status = 'running'
          AND datetime(updated_at) <= datetime('now', ?)
        """,
        (f"-{timeout} seconds",),
    ).fetchall()
    count = 0
    for row in rows:
        jid = int(row["id"])
        conn.execute(
            """
            UPDATE publish_jobs
            SET status = 'pending',
                claim_token = NULL,
                claimed_at = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (jid,),
        )
        db.log_event(
            conn,
            entity_type="publish_job",
            entity_id=jid,
            event_type="job_stale_recovered",
            payload=json.dumps(
                {
                    "article_id": int(row["article_id"]),
                    "retry_count": int(row["retry_count"] or 0),
                    "timeout_seconds": timeout,
                },
                ensure_ascii=False,
            ),
        )
        logger.warning("任务 %s 执行超时，已恢复为待发布", jid)
        count += 1
    return count


def schedule_failure_retry(
    conn: sqlite3.Connection,
    *,
    job_id: int,
    article_id: int,
    retry_count: int,
    config: AppConfig,
    failure_payload: str,
) -> str:
    """
    失败后的状态：未达上限则 pending + next_retry_at；否则 failed。
    返回最终 status。
    """
    max_retries = max_retries_for(config)
    new_retry = retry_count + 1
    if new_retry < max_retries:
        delay = retry_backoff_seconds(new_retry)
        conn.execute(
            """
            UPDATE publish_jobs
            SET status = 'pending',
                retry_count = ?,
                next_retry_at = datetime('now', ?),
                claim_token = NULL,
                claimed_at = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (new_retry, f"+{delay} seconds", int(job_id)),
        )
        db.log_event(
            conn,
            entity_type="publish_job",
            entity_id=int(job_id),
            event_type="job_retry_scheduled",
            payload=json.dumps(
                {
                    "article_id": article_id,
                    "retry_count": new_retry,
                    "delay_seconds": delay,
                    "failure": failure_payload[:500],
                },
                ensure_ascii=False,
            ),
        )
        logger.warning(
            "任务 %s 失败，%ss 后自动重试 (%s/%s)",
            job_id,
            delay,
            new_retry,
            max_retries,
        )
        return "pending"
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'failed',
            retry_count = ?,
            next_retry_at = NULL,
            claim_token = NULL,
            claimed_at = NULL,
            updated_at = datetime('now')
        WHERE id = ?
        """,
        (new_retry, int(job_id)),
    )
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=int(job_id),
        event_type="job_failed",
        payload=failure_payload,
    )
    return "failed"


def log_misfire_if_needed(
    conn: sqlite3.Connection,
    *,
    job_id: int,
    article_id: int,
    scheduled_at: str | None,
    config: AppConfig,
) -> bool:
    """计划时间早于宽限窗口则记 misfire 事件（仍会继续执行）。"""
    grace = max(1, int(getattr(config, "scheduler_misfire_grace_minutes", 60)))
    scheduled = _parse_iso(scheduled_at)
    if scheduled is None:
        return False
    threshold = datetime.now().replace(microsecond=0) - timedelta(minutes=grace)
    if scheduled > threshold:
        return False
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=int(job_id),
        event_type="job_misfire",
        payload=json.dumps(
            {
                "article_id": article_id,
                "scheduled_at": scheduled_at,
                "grace_minutes": grace,
            },
            ensure_ascii=False,
        ),
    )
    logger.info("任务 %s 已过计划时间超过 %s 分钟（misfire，仍将补发）", job_id, grace)
    return True


def _parse_iso(raw: str | None) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    normalized = text.replace(" ", "T") if "T" not in text and " " in text else text
    try:
        return datetime.fromisoformat(normalized).replace(microsecond=0)
    except ValueError:
        return None
