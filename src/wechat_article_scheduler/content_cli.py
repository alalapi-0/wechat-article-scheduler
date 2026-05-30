"""内容库 CLI 辅助。"""

from __future__ import annotations

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_library import list_collections, list_content_items


def print_content_library(config: AppConfig, *, limit: int = 20) -> int:
    with db.connect(config.database_path) as conn:
        collections = list_collections(conn)
        items = list_content_items(conn, limit=limit)
    print(f"集合 ({len(collections)}):")
    for col in collections:
        desc = f" — {col.description}" if col.description else ""
        print(f"  [{col.slug}] {col.name}{desc}")
    print(f"内容条目 (最近 {len(items)}):")
    for item in items:
        tags = ",".join(item.tags) if item.tags else "-"
        batch = item.import_batch or "-"
        print(
            f"  #{item.article_id} [{item.review_status}] {item.title!r} "
            f"col={item.collection_slug} tags={tags} batch={batch}"
        )
    return len(items)
