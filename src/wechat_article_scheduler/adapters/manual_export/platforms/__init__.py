"""各平台 manual_export 发布包模板。"""

from wechat_article_scheduler.adapters.manual_export.platforms.registry import (
    SUPPORTED_PLATFORMS,
    build_platform_pack,
)

__all__ = ["SUPPORTED_PLATFORMS", "build_platform_pack"]
