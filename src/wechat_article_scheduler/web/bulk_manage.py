"""批量管理与删除影响预览（Round 52）。"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.manager import (
    cleanup_orphan_covers as _cleanup_orphan_covers,
    list_orphan_covers as _list_orphan_covers,
)
from wechat_article_scheduler.web.trash import safe_unlink

_ACTIVE_ARTICLE = "(deleted_at IS NULL OR deleted_at = '')"


def build_delete_impact(conn: sqlite3.Connection, article_ids: list[int]) -> dict[str, Any]:
    """批量移入回收站前的影响摘要（不修改数据）。"""
    articles: list[dict[str, Any]] = []
    pending_jobs = 0
    for aid in article_ids:
        row = conn.execute(
            f"""
            SELECT id, title FROM articles
            WHERE id = ? AND {_ACTIVE_ARTICLE}
            """,
            (int(aid),),
        ).fetchone()
        if row is None:
            continue
        job_cnt = conn.execute(
            """
            SELECT COUNT(*) AS cnt FROM publish_jobs
            WHERE article_id = ? AND status = 'pending'
            """,
            (int(row["id"]),),
        ).fetchone()["cnt"]
        pending_jobs += int(job_cnt)
        articles.append(
            {
                "id": int(row["id"]),
                "title": row["title"] or "（无标题）",
                "pending_jobs": int(job_cnt),
            }
        )
    lines: list[str] = []
    if articles:
        lines.append(f"将 {len(articles)} 篇作品移入回收站")
    if pending_jobs:
        lines.append(f"其中 {pending_jobs} 个待发布任务将被取消")
    if not articles:
        lines.append("没有可删除的选中作品")
    return {
        "article_count": len(articles),
        "pending_jobs_to_cancel": pending_jobs,
        "articles": articles,
        "human": lines,
    }


def cancel_publish_job(conn: sqlite3.Connection, job_id: int) -> bool:
    row = conn.execute(
        "SELECT id, article_id, status FROM publish_jobs WHERE id = ?",
        (int(job_id),),
    ).fetchone()
    if row is None or row["status"] != "pending":
        return False
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'cancelled', updated_at = datetime('now')
        WHERE id = ?
        """,
        (int(job_id),),
    )
    db.log_event(
        conn,
        entity_type="publish_job",
        entity_id=int(job_id),
        event_type="job_cancelled",
        payload=json.dumps({"article_id": int(row["article_id"])}, ensure_ascii=False),
    )
    return True


def bulk_cancel_publish_jobs(
    conn: sqlite3.Connection, *, job_ids: list[int] | None = None
) -> dict[str, int]:
    ids = [int(x) for x in (job_ids or [])]
    ok = 0
    for jid in ids:
        if cancel_publish_job(conn, jid):
            ok += 1
    return {"requested": len(ids), "cancelled": ok}


def list_orphan_covers(cfg: AppConfig, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """列出各素材目录中未被作品引用的封面文件。"""
    return _list_orphan_covers(cfg, conn)


def cleanup_orphan_covers(cfg: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    return _cleanup_orphan_covers(cfg, conn, unlink=safe_unlink)
