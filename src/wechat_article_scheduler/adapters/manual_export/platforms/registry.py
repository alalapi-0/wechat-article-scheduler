"""平台发布包注册表。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from wechat_article_scheduler.adapters.manual_export.platforms.bilibili import (
    build_bilibili_publish_pack,
)
from wechat_article_scheduler.adapters.manual_export.platforms.douban import (
    build_douban_publish_pack,
)
from wechat_article_scheduler.adapters.manual_export.platforms.wechat_channels import (
    build_wechat_channels_publish_pack,
)
from wechat_article_scheduler.adapters.manual_export.platforms.xiaohongshu import (
    build_xiaohongshu_publish_pack,
)
from wechat_article_scheduler.adapters.manual_export.platforms.zhihu import (
    build_zhihu_publish_pack,
)

PackBuilder = Callable[..., list[str]]

SUPPORTED_PLATFORMS: dict[str, dict[str, str]] = {
    "generic": {
        "label": "通用",
        "description": "Markdown/HTML 通用 outbox，无平台专用字段",
    },
    "zhihu": {
        "label": "知乎",
        "description": "标题、导语、正文、封面说明与发布清单（仅复制，不自动发布）",
    },
    "douban": {
        "label": "豆瓣",
        "description": "标题、正文、标签提示与封面说明（仅复制，不自动发布）",
    },
    "bilibili": {
        "label": "Bilibili",
        "description": "标题、简介、封面说明、上传清单与视频占位（不自动上传）",
    },
    "xiaohongshu": {
        "label": "小红书",
        "description": "图文笔记标题、正文、话题提示与素材占位（高风控，仅人工）",
    },
    "wechat_channels": {
        "label": "微信视频号",
        "description": "视频号标题、描述、封面与视频占位；与公众号 API 分离",
    },
}

_BUILDERS: dict[str, PackBuilder] = {
    "zhihu": build_zhihu_publish_pack,
    "douban": build_douban_publish_pack,
    "bilibili": build_bilibili_publish_pack,
    "xiaohongshu": build_xiaohongshu_publish_pack,
    "wechat_channels": build_wechat_channels_publish_pack,
}


def build_platform_pack(
    dest: Path,
    *,
    platform: str,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    key = (platform or "generic").strip().lower()
    builder = _BUILDERS.get(key)
    if not builder:
        return []
    return builder(
        dest,
        title=title,
        digest=digest,
        body=body,
        has_cover=has_cover,
    )
