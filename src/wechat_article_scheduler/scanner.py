"""扫描 articles/inbox 并写入数据库。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library.collection_scan import (
    scan_collection_inboxes,
    scan_legacy_inbox_root,
)


from wechat_article_scheduler.scan_support import allowed_extensions, reconcile_reupload


def _merge_stats(target: dict[str, object], part: dict[str, object]) -> None:
    for key in (
        "scanned",
        "imported",
        "reconciled_reupload",
        "skipped_duplicate",
        "skipped_empty",
        "errors",
    ):
        target[key] = int(target.get(key, 0)) + int(part.get(key, 0))
    rec = target.setdefault("reconciled_articles", [])
    assert isinstance(rec, list)
    extra = part.get("reconciled_articles") or []
    if isinstance(extra, list):
        rec.extend(extra)


def scan_inbox(config: AppConfig) -> dict[str, int | list | dict]:
    """
    扫描收件箱：根目录 articles/inbox → 默认合集；各合集 inbox → 对应合集。

    返回统计：scanned, imported, reconciled_reupload, skipped_duplicate, errors,
    reconciled_articles, collections（各合集子统计）
    """
    stats: dict[str, object] = {
        "scanned": 0,
        "imported": 0,
        "reconciled_reupload": 0,
        "skipped_duplicate": 0,
        "errors": 0,
        "reconciled_articles": [],
        "collections": {},
    }
    inbox = config.inbox_dir
    if not inbox.exists():
        inbox.mkdir(parents=True, exist_ok=True)

    with db.connect(config.database_path) as conn:
        legacy = scan_legacy_inbox_root(config, conn)
        _merge_stats(stats, legacy)
        coll_stats = scan_collection_inboxes(config, conn)
        _merge_stats(stats, coll_stats)
        coll_map = coll_stats.get("collections")
        if isinstance(coll_map, dict):
            stats["collections"] = coll_map

    return stats  # type: ignore[return-value]


# 向后兼容别名
_reconcile_reupload = reconcile_reupload
_allowed_extensions = allowed_extensions
