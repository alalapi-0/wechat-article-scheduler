"""browser_assist 多平台干跑计划入口。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.adapters.browser_assist.workflow import (
    build_dry_run_plan as build_wechat_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.zhihu_workflow import (
    build_zhihu_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.douban_workflow import (
    build_douban_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.bilibili_workflow import (
    build_bilibili_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.wechat_channels_workflow import (
    build_wechat_channels_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.xiaohongshu_workflow import (
    build_xiaohongshu_dry_run_plan,
)
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.adapters.manual_export import list_outbox_packages

SUPPORTED_BROWSER_ASSIST: dict[str, dict[str, str]] = {
    "wechat_official": {
        "label": "微信公众号",
        "description": "草稿箱辅助、API 缺口字段核对",
    },
    "zhihu": {
        "label": "知乎",
        "description": "创作页辅助评估（dry-run，不自动发布）",
    },
    "douban": {
        "label": "豆瓣",
        "description": "日记/笔记辅助评估（dry-run，不自动发布）",
    },
    "bilibili": {
        "label": "Bilibili",
        "description": "视频投稿页辅助评估（dry-run，不自动上传）",
    },
    "xiaohongshu": {
        "label": "小红书",
        "description": "图文/视频笔记辅助评估（dry-run，高风控）",
    },
    "wechat_channels": {
        "label": "微信视频号",
        "description": "视频号助手辅助评估（dry-run，非公众号 API）",
    },
}


def _latest_outbox_path(config: AppConfig | None, article_id: str | None, platform: str) -> str | None:
    if config is None or not article_id:
        return None
    try:
        aid = int(article_id)
    except (TypeError, ValueError):
        return None
    for item in list_outbox_packages(config, limit=50):
        if item.get("article_id") == aid and item.get("platform") == platform:
            return item.get("relative_path")
    return None


def build_dry_run_plan(
    *,
    platform: str = "wechat_official",
    article_id: str | None = None,
    media_id: str | None = None,
    outbox_relative_path: str | None = None,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    key = (platform or "wechat_official").strip().lower()
    if key == "zhihu":
        ob = outbox_relative_path or _latest_outbox_path(config, article_id, "zhihu")
        return build_zhihu_dry_run_plan(
            article_id=article_id,
            outbox_relative_path=ob,
        )
    if key == "douban":
        ob = outbox_relative_path or _latest_outbox_path(config, article_id, "douban")
        return build_douban_dry_run_plan(
            article_id=article_id,
            outbox_relative_path=ob,
        )
    if key == "bilibili":
        ob = outbox_relative_path or _latest_outbox_path(config, article_id, "bilibili")
        return build_bilibili_dry_run_plan(
            article_id=article_id,
            outbox_relative_path=ob,
        )
    if key in ("xiaohongshu", "xhs"):
        ob = outbox_relative_path or _latest_outbox_path(config, article_id, "xiaohongshu")
        return build_xiaohongshu_dry_run_plan(
            article_id=article_id,
            outbox_relative_path=ob,
        )
    if key in ("wechat_channels", "channels", "video_account"):
        ob = outbox_relative_path or _latest_outbox_path(config, article_id, "wechat_channels")
        return build_wechat_channels_dry_run_plan(
            article_id=article_id,
            outbox_relative_path=ob,
        )
    if key in ("wechat", "wechat_official"):
        return build_wechat_dry_run_plan(article_id=article_id, media_id=media_id)
    raise ValueError(f"不支持的 browser_assist 平台：{platform}")
