"""多合集收件箱扫描（兼容 articles/inbox 根目录）。"""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library.collection_config import (
    CollectionConfig,
    apply_title_template,
    discover_collection_configs,
)
from wechat_article_scheduler.content_library.repository import (
    apply_collection_defaults,
    ensure_default_collection,
    register_imported_article,
    upsert_collection,
)
from wechat_article_scheduler.dedupe import find_existing_article
from wechat_article_scheduler.parser import parse_file_snapshot
from wechat_article_scheduler.scan_support import allowed_extensions
from wechat_article_scheduler.filesystem_safety import (
    DirectoryHandle,
    FileSnapshot,
    UnsafePathError,
    move_file_snapshot,
    open_directory_handle,
    path_chain_is_unaliased,
    safe_directory_exists,
)


def _reconcile_reupload_from_handle(
    conn: sqlite3.Connection,
    *,
    existing_id: int,
    inbox_handle: DirectoryHandle,
    name: str,
    reason: str,
    source_snapshot: FileSnapshot,
) -> dict[str, object]:
    if not inbox_handle.unlink_if_unchanged(name, source_snapshot):
        raise UnsafePathError("重新上传文件在处理期间发生变化")
    row = conn.execute(
        "SELECT id, title, status, deleted_at FROM articles WHERE id = ?",
        (existing_id,),
    ).fetchone()
    status_reset = False
    if row and row["deleted_at"] not in (None, ""):
        conn.execute(
            "UPDATE articles SET status = 'imported', deleted_at = NULL, "
            "updated_at = datetime('now') WHERE id = ?",
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


def _scan_directory(
    config: AppConfig,
    conn: sqlite3.Connection,
    *,
    inbox: Path,
    collection_id: int,
    coll_cfg: CollectionConfig | None,
    imported_dir: Path,
    exts: set[str],
    summary_max: int,
    rules: dict[str, Any],
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "scanned": 0,
        "imported": 0,
        "reconciled_reupload": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "reconciled_articles": [],
    }
    if not path_chain_is_unaliased(inbox) or not safe_directory_exists(inbox, allowed_roots=(inbox,)):
        return stats
    try:
        directory = open_directory_handle(inbox, allowed_roots=(inbox,))
    except (OSError, UnsafePathError):
        return stats
    try:
        with directory as inbox_handle:
            names = inbox_handle.list_names()
            for name in names:
                path = inbox / name
                if path.suffix.lower() not in exts:
                    continue
                stats["scanned"] += 1
                try:
                    snapshot = inbox_handle.read_regular_file(name)
                    parsed = parse_file_snapshot(
                        path, snapshot, summary_max_chars=summary_max
                    )
                    if not (parsed.body or "").strip():
                        stats["errors"] = int(stats.get("errors", 0)) + 1
                        stats["skipped_empty"] = int(stats.get("skipped_empty", 0)) + 1
                        db.log_event(
                            conn,
                            entity_type="article",
                            entity_id=None,
                            event_type="scan_skipped_empty",
                            payload=path.name,
                        )
                        continue
                    if coll_cfg and coll_cfg.title_template:
                        parsed = replace(
                            parsed,
                            title=apply_title_template(coll_cfg.title_template, parsed.title),
                        )
                    existing_id, reason = find_existing_article(conn, parsed, rules)
                    if existing_id is not None:
                        info = _reconcile_reupload_from_handle(
                            conn,
                            existing_id=existing_id,
                            inbox_handle=inbox_handle,
                            name=name,
                            reason=reason,
                            source_snapshot=snapshot,
                        )
                        stats["reconciled_reupload"] = int(stats["reconciled_reupload"]) + 1
                        reconciled = stats["reconciled_articles"]
                        assert isinstance(reconciled, list)
                        reconciled.append(info)
                        continue

                    dest = move_file_snapshot(
                        path,
                        imported_dir,
                        snapshot,
                        source_roots=(inbox,),
                        destination_roots=(config.articles_dir,),
                        source_directory=inbox_handle,
                    )
                    cur = conn.execute(
                        """
                        INSERT INTO articles (source_path, title, summary, body, content_hash, status)
                        VALUES (?, ?, ?, ?, ?, 'imported')
                        """,
                        (str(dest), parsed.title, parsed.summary, parsed.body, parsed.content_hash),
                    )
                    article_id = int(cur.lastrowid)
                    register_imported_article(conn, article_id=article_id, collection_id=collection_id)
                    apply_collection_defaults(conn, config.root, article_id, coll_cfg)
                    conn.commit()
                    db.log_event(
                        conn,
                        entity_type="article",
                        entity_id=article_id,
                        event_type="scan_imported",
                        payload=f"{coll_cfg.slug if coll_cfg else 'default'}:{path.name}",
                    )
                    stats["imported"] += 1
                except (OSError, UnsafePathError):
                    stats["errors"] += 1
                    db.log_event(
                        conn,
                        entity_type="article",
                        entity_id=None,
                        event_type="scan_error",
                        payload=path.name,
                    )
    except (OSError, UnsafePathError):
        return stats
    return stats


def _merge_stats(target: dict[str, Any], part: dict[str, Any]) -> None:
    for key in ("scanned", "imported", "reconciled_reupload", "skipped_duplicate", "errors"):
        target[key] = int(target.get(key, 0)) + int(part.get(key, 0))
    rec = target.setdefault("reconciled_articles", [])
    assert isinstance(rec, list)
    extra = part.get("reconciled_articles") or []
    if isinstance(extra, list):
        rec.extend(extra)


def sync_discovered_collections(config: AppConfig, conn: sqlite3.Connection) -> list[CollectionConfig]:
    configs = discover_collection_configs(config.root)
    for cfg in configs:
        upsert_collection(conn, cfg)
    conn.commit()
    return configs


def scan_collection_inboxes(config: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    """扫描各合集 inbox；不处理 articles/inbox 根目录直放文件。"""
    totals: dict[str, Any] = {
        "scanned": 0,
        "imported": 0,
        "reconciled_reupload": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "reconciled_articles": [],
        "collections": {},
    }
    configs = sync_discovered_collections(config, conn)
    exts = allowed_extensions(config.rules)
    scan_rules = config.rules.get("scan", {}) if isinstance(config.rules.get("scan"), dict) else {}
    summary_max = int(scan_rules.get("summary_max_chars", 120))
    imported_root = config.imported_dir

    for coll_cfg in configs:
        coll_id = upsert_collection(conn, coll_cfg)
        coll_imported = imported_root / coll_cfg.slug
        part_total: dict[str, Any] = {
            "scanned": 0,
            "imported": 0,
            "reconciled_reupload": 0,
            "errors": 0,
        }
        for inbox in coll_cfg.inbox_dirs:
            part = _scan_directory(
                config,
                conn,
                inbox=inbox,
                collection_id=coll_id,
                coll_cfg=coll_cfg,
                imported_dir=coll_imported,
                exts=exts,
                summary_max=summary_max,
                rules=config.rules,
            )
            _merge_stats(part_total, part)
            _merge_stats(totals, part)
        totals["collections"][coll_cfg.slug] = part_total
    return totals


def scan_legacy_inbox_root(config: AppConfig, conn: sqlite3.Connection) -> dict[str, Any]:
    """扫描 articles/inbox 根目录直放文件 → 默认合集。"""
    default_id = ensure_default_collection(conn)
    scan_rules = config.rules.get("scan", {}) if isinstance(config.rules.get("scan"), dict) else {}
    summary_max = int(scan_rules.get("summary_max_chars", 120))
    return _scan_directory(
        config,
        conn,
        inbox=config.inbox_dir,
        collection_id=default_id,
        coll_cfg=None,
        imported_dir=config.imported_dir,
        exts=allowed_extensions(config.rules),
        summary_max=summary_max,
        rules=config.rules,
    )
