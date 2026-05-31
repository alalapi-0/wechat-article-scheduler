"""扫描 articles/inbox 并写入数据库。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library import register_imported_article
from wechat_article_scheduler.dedupe import find_existing_article
from wechat_article_scheduler.parser import parse_file


def _reconcile_reupload(
    conn: sqlite3.Connection,
    *,
    existing_id: int,
    inbox_path: Path,
    reason: str,
) -> dict[str, object]:
    """重复上传时绑定已有作品：清理 inbox 临时文件，必要时重置发布状态。"""
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


def _allowed_extensions(rules: dict[str, Any]) -> set[str]:
    scan = rules.get("scan", {}) if isinstance(rules.get("scan"), dict) else {}
    exts = scan.get("extensions", [".md", ".txt", ".html"])
    return {e if e.startswith(".") else f".{e}" for e in exts}


def scan_inbox(config: AppConfig) -> dict[str, int]:
    """
    扫描 inbox 目录：解析、去重、入库并移动到 imported。

    返回统计：scanned, imported, reconciled_reupload, skipped_duplicate, errors,
    reconciled_articles（重复上传时绑定的已有作品列表）
    """
    stats: dict[str, object] = {
        "scanned": 0,
        "imported": 0,
        "reconciled_reupload": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "reconciled_articles": [],
    }
    inbox = config.inbox_dir
    if not inbox.exists():
        inbox.mkdir(parents=True, exist_ok=True)
        return stats

    imported_dir = config.imported_dir
    imported_dir.mkdir(parents=True, exist_ok=True)

    exts = _allowed_extensions(config.rules)
    scan_rules = config.rules.get("scan", {}) if isinstance(config.rules.get("scan"), dict) else {}
    summary_max = int(scan_rules.get("summary_max_chars", 120))

    with db.connect(config.database_path) as conn:
        for path in sorted(inbox.iterdir()):
            if not path.is_file() or path.suffix.lower() not in exts:
                continue
            stats["scanned"] += 1
            try:
                parsed = parse_file(path, summary_max_chars=summary_max)
                existing_id, reason = find_existing_article(conn, parsed, config.rules)
                if existing_id is not None:
                    info = _reconcile_reupload(
                        conn,
                        existing_id=existing_id,
                        inbox_path=path,
                        reason=reason,
                    )
                    stats["reconciled_reupload"] = int(stats["reconciled_reupload"]) + 1
                    reconciled = stats["reconciled_articles"]
                    assert isinstance(reconciled, list)
                    reconciled.append(info)
                    continue

                cur = conn.execute(
                    """
                    INSERT INTO articles (source_path, title, summary, body, content_hash, status)
                    VALUES (?, ?, ?, ?, ?, 'imported')
                    """,
                    (parsed.source_path, parsed.title, parsed.summary, parsed.body, parsed.content_hash),
                )
                article_id = int(cur.lastrowid)
                register_imported_article(conn, article_id=article_id)
                dest = imported_dir / path.name
                shutil.move(str(path), str(dest))
                conn.execute(
                    "UPDATE articles SET source_path = ?, updated_at = datetime('now') WHERE id = ?",
                    (str(dest), article_id),
                )
                conn.commit()
                db.log_event(
                    conn,
                    entity_type="article",
                    entity_id=article_id,
                    event_type="scan_imported",
                    payload=path.name,
                )
                stats["imported"] += 1
            except OSError:
                stats["errors"] += 1
                db.log_event(
                    conn,
                    entity_type="article",
                    entity_id=None,
                    event_type="scan_error",
                    payload=path.name,
                )

    return stats
