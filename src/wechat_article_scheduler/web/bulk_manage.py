"""批量管理与删除影响预览（Round 52）。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.web.trash import _resolve_under, safe_unlink

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


def _referenced_cover_paths(cfg: AppConfig, conn: sqlite3.Connection) -> set[Path]:
    refs: set[Path] = set()
    rows = conn.execute(
        "SELECT cover_path FROM articles WHERE cover_path IS NOT NULL AND cover_path != ''"
    ).fetchall()
    for row in rows:
        resolved = _resolve_under(cfg.root, row["cover_path"] or "")
        if resolved is not None:
            refs.add(resolved)
    if cfg.wechat_default_thumb_path:
        resolved = _resolve_under(cfg.root, cfg.wechat_default_thumb_path)
        if resolved is not None:
            refs.add(resolved)
    return refs


def list_orphan_covers(cfg: AppConfig, conn: sqlite3.Connection) -> list[dict[str, str]]:
    """列出 covers 目录中未被任何作品引用的封面文件。"""
    refs = _referenced_cover_paths(cfg, conn)
    covers_dir = cfg.covers_dir
    if not covers_dir.is_dir():
        return []
    orphans: list[dict[str, str]] = []
    for path in sorted(covers_dir.iterdir()):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved in refs:
            continue
        try:
            rel = str(resolved.relative_to(cfg.root.resolve()))
        except ValueError:
            rel = str(path)
        orphans.append({"path": rel, "name": path.name})
    return orphans


def cleanup_orphan_covers(cfg: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    items = list_orphan_covers(cfg, conn)
    removed = 0
    for item in items:
        if safe_unlink(cfg, item["path"]):
            removed += 1
    return {
        "scanned": len(items),
        "removed": removed,
        "orphans": items,
        "human": [
            f"已清理 {removed} 个未引用封面文件"
            if removed
            else "没有发现可安全删除的未引用封面",
        ],
    }
