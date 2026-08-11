"""作品回收站：软删除、恢复与彻底清理。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import inspect_managed_cover
from wechat_article_scheduler.content_library.collection_config import discover_collection_configs
from wechat_article_scheduler.filesystem_safety import (
    DirectoryHandle,
    FileSnapshot,
    UnsafePathError,
    read_regular_file,
    unlink_if_unchanged,
)

_ACTIVE = "(deleted_at IS NULL OR deleted_at = '')"


def safe_unlink(
    cfg: AppConfig,
    raw: str,
    *,
    directory_handle: DirectoryHandle | None = None,
    snapshot: FileSnapshot | None = None,
) -> bool:
    """Delete only an unaliased regular file without following any symlink."""
    path = Path(raw)
    if not path.is_absolute():
        path = cfg.root / path
    roots = (cfg.articles_dir, cfg.root / "cover_assets", cfg.root / "assets" / "covers")
    if directory_handle is not None or snapshot is not None:
        if directory_handle is None or snapshot is None:
            return False
        if Path(path.absolute()).parent != directory_handle.path:
            return False
        return directory_handle.unlink_if_unchanged(path.name, snapshot)
    try:
        snapshot = read_regular_file(path, allowed_roots=roots)
    except UnsafePathError:
        return False
    return unlink_if_unchanged(path, snapshot, allowed_roots=roots)


def _managed_file_identity(cfg: AppConfig, raw: str) -> tuple[int, int] | None:
    path = Path(raw)
    if not path.is_absolute():
        path = cfg.root / path
    try:
        snapshot = read_regular_file(
            path,
            allowed_roots=(
                cfg.articles_dir,
                cfg.root / "cover_assets",
                cfg.root / "assets" / "covers",
            ),
        )
    except UnsafePathError:
        return None
    return snapshot.device, snapshot.inode


def _other_managed_reference(
    conn: sqlite3.Connection, cfg: AppConfig, article_id: int, raw: str
) -> bool:
    current = _managed_file_identity(cfg, raw)
    if current is None:
        return False
    global_default = str(cfg.wechat_default_thumb_path or "").strip()
    if global_default and _managed_file_identity(cfg, global_default) == current:
        return True
    rows = conn.execute(
        "SELECT source_path, cover_path FROM articles WHERE id != ?",
        (article_id,),
    ).fetchall()
    for row in rows:
        for field in ("source_path", "cover_path"):
            other = _managed_file_identity(cfg, str(row[field] or ""))
            if other == current:
                return True
    for collection in discover_collection_configs(cfg.root):
        if not collection.default_cover:
            continue
        if _managed_file_identity(cfg, str(collection.default_cover)) == current:
            return True
    return False


def reset_article_schedule_state_if_unplanned(
    conn: sqlite3.Connection,
    article_id: int,
) -> None:
    """取消本地计划后，让已收录作品重新进入可排期状态。"""
    row = conn.execute(
        "SELECT status FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()
    if row is None or row["status"] != "imported":
        return
    active = conn.execute(
        """
        SELECT 1 FROM publish_jobs
        WHERE article_id = ? AND status IN ('pending', 'running')
        LIMIT 1
        """,
        (article_id,),
    ).fetchone()
    if active is None:
        conn.execute(
            "UPDATE articles SET schedule_state = 'imported', updated_at = datetime('now') "
            "WHERE id = ?",
            (article_id,),
        )


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
    reset_article_schedule_state_if_unplanned(conn, article_id)
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
    reset_article_schedule_state_if_unplanned(conn, article_id)
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
        raw = row[field] or ""
        if not raw:
            continue
        if _other_managed_reference(conn, cfg, article_id, raw):
            continue
        if field == "cover_path" and not inspect_managed_cover(cfg, raw)["ok"]:
            continue
        if safe_unlink(cfg, raw):
            files_removed += 1
    job_ids = [
        int(item["id"])
        for item in conn.execute(
            "SELECT id FROM publish_jobs WHERE article_id = ?",
            (article_id,),
        ).fetchall()
    ]
    draft_ids = [
        int(item["id"])
        for item in conn.execute(
            "SELECT id FROM wechat_drafts WHERE article_id = ?",
            (article_id,),
        ).fetchall()
    ]
    conn.execute("DELETE FROM publish_proofs WHERE article_id = ?", (article_id,))
    for job_id in job_ids:
        conn.execute(
            "DELETE FROM events WHERE entity_type = 'publish_job' AND entity_id = ?",
            (job_id,),
        )
    for draft_id in draft_ids:
        conn.execute(
            "DELETE FROM events WHERE entity_type = 'wechat_draft' AND entity_id = ?",
            (draft_id,),
        )
    conn.execute("DELETE FROM publish_jobs WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM wechat_drafts WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM article_tags WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    conn.execute(
        "DELETE FROM events WHERE entity_type = 'article' AND entity_id = ?",
        (article_id,),
    )
    return {"article_id": article_id, "removed": True, "files_removed": files_removed}


def purge_trash(cfg: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    # Reference checks and local unlinks must share one DB write-locked window;
    # otherwise another connection could add a reference after the check.
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    else:
        conn.execute("UPDATE articles SET updated_at = updated_at WHERE 0")
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
