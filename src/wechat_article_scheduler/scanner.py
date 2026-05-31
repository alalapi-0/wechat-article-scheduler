"""扫描 articles/inbox 并写入数据库。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library import register_imported_article
from wechat_article_scheduler.dedupe import is_duplicate
from wechat_article_scheduler.parser import parse_file


def _allowed_extensions(rules: dict[str, Any]) -> set[str]:
    scan = rules.get("scan", {}) if isinstance(rules.get("scan"), dict) else {}
    exts = scan.get("extensions", [".md", ".txt", ".html"])
    return {e if e.startswith(".") else f".{e}" for e in exts}


def scan_inbox(config: AppConfig) -> dict[str, int]:
    """
    扫描 inbox 目录：解析、去重、入库并移动到 imported。

    返回统计：scanned, imported, skipped_duplicate, errors
    """
    stats = {"scanned": 0, "imported": 0, "skipped_duplicate": 0, "errors": 0}
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
                dup, reason = is_duplicate(conn, parsed, config.rules)
                if dup:
                    stats["skipped_duplicate"] += 1
                    db.log_event(
                        conn,
                        entity_type="article",
                        entity_id=None,
                        event_type="scan_skipped_duplicate",
                        payload=reason,
                    )
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
