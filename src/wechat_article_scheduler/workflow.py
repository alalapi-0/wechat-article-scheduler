"""Round 1：驳回与失败重试。"""

from __future__ import annotations

import shutil
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig


def reject_article(config: AppConfig, article_id: int) -> bool:
    """将文章从发布流程中移除（标为 rejected）并移到 articles/rejected。"""
    rejected_dir = config.rejected_dir
    rejected_dir.mkdir(parents=True, exist_ok=True)

    with db.connect(config.database_path) as conn:
        row = conn.execute("SELECT id, source_path, status FROM articles WHERE id = ?", (article_id,)).fetchone()
        if row is None:
            return False
        src = Path(row["source_path"])
        if src.exists():
            dest = rejected_dir / src.name
            if dest.exists():
                dest = rejected_dir / f"{src.stem}_{article_id}{src.suffix}"
            shutil.move(str(src), str(dest))
            conn.execute("UPDATE articles SET source_path = ? WHERE id = ?", (str(dest), article_id))
        conn.execute(
            "UPDATE articles SET status = 'rejected', updated_at = datetime('now') WHERE id = ?",
            (article_id,),
        )
        conn.execute(
            "UPDATE publish_jobs SET status = 'cancelled', updated_at = datetime('now') "
            "WHERE article_id = ? AND status IN ('pending', 'running')",
            (article_id,),
        )
        db.log_event(conn, entity_type="article", entity_id=article_id, event_type="rejected")
        conn.commit()
    return True


def _reset_job_to_pending(conn, job_id: int) -> bool:
    row = conn.execute(
        "SELECT id, status FROM publish_jobs WHERE id = ?",
        (int(job_id),),
    ).fetchone()
    if row is None or row["status"] != "failed":
        return False
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'pending', retry_count = 0, updated_at = datetime('now')
        WHERE id = ?
        """,
        (int(job_id),),
    )
    db.log_event(conn, entity_type="publish_job", entity_id=int(job_id), event_type="retry_failed")
    return True


def retry_publish_job(config: AppConfig, job_id: int) -> bool:
    """将单条 failed 任务重置为 pending。"""
    with db.connect(config.database_path) as conn:
        ok = _reset_job_to_pending(conn, job_id)
        if ok:
            conn.commit()
        return ok


def retry_failed_jobs(config: AppConfig, job_ids: list[int] | None = None) -> int:
    """将 failed 的 publish_jobs 重置为 pending（可指定 id 列表）。"""
    count = 0
    with db.connect(config.database_path) as conn:
        if job_ids:
            ids = [int(x) for x in job_ids]
            for jid in ids:
                if _reset_job_to_pending(conn, jid):
                    count += 1
        else:
            rows = conn.execute("SELECT id FROM publish_jobs WHERE status = 'failed'").fetchall()
            for row in rows:
                if _reset_job_to_pending(conn, int(row["id"])):
                    count += 1
        conn.commit()
    return count
