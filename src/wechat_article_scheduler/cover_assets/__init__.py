"""封面素材管理。"""

from wechat_article_scheduler.cover_assets.index import (
    CoverAsset,
    check_cover_path,
    index_cover_directory,
)
from wechat_article_scheduler.cover_assets.crop_preview import (
    build_dual_cover_previews,
    crop_for_aspect,
    enrich_cover_config,
    pillow_available,
)
from wechat_article_scheduler.cover_assets.manager import (
    bind_covers_by_stem,
    build_disk_stem_index,
    cleanup_orphan_covers,
    list_orphan_covers,
    managed_cover_directories,
    repair_invalid_cover_paths,
    scan_cover_assets,
)

__all__ = [
    "CoverAsset",
    "build_dual_cover_previews",
    "bind_covers_by_stem",
    "crop_for_aspect",
    "enrich_cover_config",
    "pillow_available",
    "build_disk_stem_index",
    "check_cover_path",
    "cleanup_orphan_covers",
    "index_cover_directory",
    "list_orphan_covers",
    "managed_cover_directories",
    "repair_invalid_cover_paths",
    "scan_cover_assets",
]
