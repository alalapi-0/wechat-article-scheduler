"""扫描共用逻辑（避免 scanner 与 collection_scan 循环导入）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.filesystem_safety import FileSnapshot, UnsafePathError, unlink_if_unchanged


def allowed_extensions(rules: dict[str, Any]) -> set[str]:
    scan = rules.get("scan", {}) if isinstance(rules.get("scan"), dict) else {}
    exts = scan.get("extensions", [".md", ".txt", ".html"])
    return {e if e.startswith(".") else f".{e}" for e in exts}


def reconcile_reupload(
    conn: sqlite3.Connection,
    *,
    existing_id: int,
    inbox_path: Path,
    reason: str,
    source_snapshot: FileSnapshot,
) -> dict[str, object]:
    if not unlink_if_unchanged(inbox_path, source_snapshot, allowed_roots=(inbox_path.parent,)):
        raise UnsafePathError("重新上传文件在处理期间发生变化")
    row = conn.execute(
        "SELECT id, title, status, deleted_at FROM articles WHERE id = ?",
        (existing_id,),
    ).fetchone()
    status_reset = False
    if row and row["deleted_at"] is not None and row["deleted_at"] != "":
        conn.execute(
            """
            UPDATE articles
            SET status = 'imported', deleted_at = NULL, updated_at = datetime('now')
            WHERE id = ?
            """,
            (existing_id,),
        )
        status_reset = row["status"] == "published"
    elif row and row["status"] == "published":
        conn.execute(
            "UPDATE articles SET status = 'imported', updated_at = datetime('now') WHERE id = ?",
            (existing_id,),
        )
        status_reset = True
    elif row:
        conn.execute(
            "UPDATE articles SET updated_at = datetime('now') WHERE id = ?",
            (existing_id,),
        )
    db.log_event(
        conn,
        entity_type="article",
        entity_id=existing_id,
        event_type="scan_reupload_reconciled",
        payload=reason,
    )
    conn.commit()
    return {
        "id": existing_id,
        "title": row["title"] if row else "",
        "status_reset": status_reset,
    }
