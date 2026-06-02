"""内容库：集合、标签与审核状态。"""

from wechat_article_scheduler.content_library.models import (
    Collection,
    ContentItem,
    Tag,
)
from wechat_article_scheduler.content_library.collection_config import (
    CollectionConfig,
    discover_collection_configs,
    load_collection_yaml,
)
from wechat_article_scheduler.content_library.collection_scan import (
    scan_collection_inboxes,
    sync_discovered_collections,
)
from wechat_article_scheduler.content_library.repository import (
    ensure_default_collection,
    list_collections,
    list_collections_summary,
    list_content_items,
    register_imported_article,
    upsert_collection,
)

__all__ = [
    "Collection",
    "CollectionConfig",
    "ContentItem",
    "Tag",
    "discover_collection_configs",
    "ensure_default_collection",
    "list_collections",
    "list_collections_summary",
    "list_content_items",
    "load_collection_yaml",
    "register_imported_article",
    "scan_collection_inboxes",
    "sync_discovered_collections",
    "upsert_collection",
]
