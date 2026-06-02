"""扫描共用逻辑（避免 scanner 与 collection_scan 循环导入）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db


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
) -> dict[str, object]:
    row = conn.execute(
        "SELECT id, title, status FROM articles WHERE id = ?",
        (existing_id,),
    ).fetchone()
    status_reset = False
    if row and row["status"] == "published":
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
    if inbox_path.is_file():
        inbox_path.unlink()
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
