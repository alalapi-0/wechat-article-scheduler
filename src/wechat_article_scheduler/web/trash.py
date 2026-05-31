"""作品回收站：软删除、恢复与彻底清理。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig

_ACTIVE = "(deleted_at IS NULL OR deleted_at = '')"


def _resolve_under(root: Path, raw: str) -> Path | None:
    if not raw or not str(raw).strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    root_resolved = root.resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError:
        return None
    return path


def safe_unlink(cfg: AppConfig, raw: str) -> bool:
    """仅删除项目根目录内的文件，避免误删系统路径。"""
    path = _resolve_under(cfg.root, raw)
    if path is None or not path.is_file():
        return False
    path.unlink(missing_ok=True)
    return True


def soft_delete_article(conn: sqlite3.Connection, article_id: int) -> bool:
    row = conn.execute(
        f"SELECT id FROM articles WHERE id = ? AND {_ACTIVE}",
        (article_id,),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE articles SET deleted_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
        (article_id,),
    )
    conn.execute(
        """
        UPDATE publish_jobs
        SET status = 'cancelled', updated_at = datetime('now')
        WHERE article_id = ? AND status = 'pending'
        """,
        (article_id,),
    )
    db.log_event(
        conn,
        entity_type="article",
        entity_id=article_id,
        event_type="article_trashed",
        payload=json.dumps({"article_id": article_id}),
    )
    return True


def restore_article(conn: sqlite3.Connection, article_id: int) -> bool:
    row = conn.execute(
        "SELECT id FROM articles WHERE id = ? AND deleted_at IS NOT NULL AND deleted_at != ''",
        (article_id,),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE articles SET deleted_at = NULL, updated_at = datetime('now') WHERE id = ?",
        (article_id,),
    )
    db.log_event(
        conn,
        entity_type="article",
        entity_id=article_id,
        event_type="article_restored",
        payload=json.dumps({"article_id": article_id}),
    )
    return True


def list_trash_articles(conn: sqlite3.Connection, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT id, title, summary, status, source_path, cover_path,
               created_at, updated_at, deleted_at
        FROM articles
        WHERE deleted_at IS NOT NULL AND deleted_at != ''
        ORDER BY deleted_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        row["has_cover"] = bool((row.get("cover_path") or "").strip())
        row["cover_url"] = f"/media/cover/{row['id']}" if row["has_cover"] else None
        out.append(row)
    return out


def _purge_article_row(conn: sqlite3.Connection, cfg: AppConfig, article_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT id, source_path, cover_path FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()
    if row is None:
        return {"article_id": article_id, "removed": False}
    files_removed = 0
    for field in ("source_path", "cover_path"):
        if safe_unlink(cfg, row[field] or ""):
            files_removed += 1
    conn.execute("DELETE FROM publish_jobs WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM wechat_drafts WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.log_event(
        conn,
        entity_type="article",
        entity_id=article_id,
        event_type="article_purged",
        payload=json.dumps({"files_removed": files_removed}),
    )
    return {"article_id": article_id, "removed": True, "files_removed": files_removed}


def purge_trash(cfg: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT id FROM articles WHERE deleted_at IS NOT NULL AND deleted_at != ''"
    ).fetchall()
    results = [_purge_article_row(conn, cfg, int(r["id"])) for r in rows]
    removed = sum(1 for r in results if r.get("removed"))
    return {"purged": removed, "details": results}


def bulk_soft_delete(conn: sqlite3.Connection, ids: list[int]) -> dict[str, int]:
    ok = 0
    for aid in ids:
        if soft_delete_article(conn, aid):
            ok += 1
    return {"requested": len(ids), "deleted": ok}


def bulk_restore(conn: sqlite3.Connection, ids: list[int]) -> dict[str, int]:
    ok = 0
    for aid in ids:
        if restore_article(conn, aid):
            ok += 1
    return {"requested": len(ids), "restored": ok}
