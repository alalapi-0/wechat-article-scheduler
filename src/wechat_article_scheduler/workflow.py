"""Round 1：驳回与失败重试。"""

from __future__ import annotations

import shutil
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig


def reject_article(config: AppConfig, article_id: int) -> bool:
    """将文章标为 rejected 并移到 articles/rejected。"""
    rejected_dir = config.root / "articles" / "rejected"
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


def retry_failed_jobs(config: AppConfig) -> int:
    """将 failed 的 publish_jobs 重置为 pending。"""
    count = 0
    with db.connect(config.database_path) as conn:
        rows = conn.execute("SELECT id FROM publish_jobs WHERE status = 'failed'").fetchall()
        for row in rows:
            conn.execute(
                """
                UPDATE publish_jobs
                SET status = 'pending', retry_count = 0, updated_at = datetime('now')
                WHERE id = ?
                """,
                (int(row["id"]),),
            )
            db.log_event(conn, entity_type="publish_job", entity_id=int(row["id"]), event_type="retry_failed")
            count += 1
        conn.commit()
    return count
