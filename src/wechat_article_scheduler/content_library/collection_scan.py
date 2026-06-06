"""多合集收件箱扫描（兼容 articles/inbox 根目录）。"""

from __future__ import annotations

import shutil
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
from wechat_article_scheduler.parser import parse_file
from wechat_article_scheduler.scan_support import allowed_extensions, reconcile_reupload


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
    if not inbox.is_dir():
        return stats
    for path in sorted(inbox.iterdir()):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        stats["scanned"] += 1
        try:
            parsed = parse_file(path, summary_max_chars=summary_max)
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
                info = reconcile_reupload(
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
            register_imported_article(conn, article_id=article_id, collection_id=collection_id)
            apply_collection_defaults(conn, config.root, article_id, coll_cfg)
            dest = imported_dir / path.name
            if dest.exists():
                stem, suffix = dest.stem, dest.suffix
                n = 1
                while dest.exists():
                    dest = imported_dir / f"{stem}_{n}{suffix}"
                    n += 1
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
                payload=f"{coll_cfg.slug if coll_cfg else 'default'}:{path.name}",
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
        coll_imported.mkdir(parents=True, exist_ok=True)
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
    config.imported_dir.mkdir(parents=True, exist_ok=True)
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
