"""封面素材管理。"""

from wechat_article_scheduler.cover_assets.index import (
    CoverAsset,
    InvalidCoverError,
    SUPPORTED_COVER_EXTENSIONS,
    check_cover_path,
    check_configured_cover,
    index_cover_directory,
    inspect_managed_cover,
    inspect_cover_path,
    managed_cover_bytes,
    managed_cover_roots,
    secure_cover_bytes,
    validate_image_bytes,
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
    "InvalidCoverError",
    "SUPPORTED_COVER_EXTENSIONS",
    "build_dual_cover_previews",
    "bind_covers_by_stem",
    "crop_for_aspect",
    "enrich_cover_config",
    "pillow_available",
    "build_disk_stem_index",
    "check_cover_path",
    "check_configured_cover",
    "cleanup_orphan_covers",
    "index_cover_directory",
    "inspect_managed_cover",
    "inspect_cover_path",
    "managed_cover_bytes",
    "managed_cover_roots",
    "list_orphan_covers",
    "managed_cover_directories",
    "repair_invalid_cover_paths",
    "scan_cover_assets",
    "secure_cover_bytes",
    "validate_image_bytes",
]
