"""微信 API 适配器工厂。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.base import WechatAdapter
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import managed_cover_roots


def get_adapter(config: AppConfig) -> WechatAdapter:
    """根据 WECHAT_MODE 返回适配器（默认 mock）。"""
    mode = str(config.wechat_mode).strip().lower()
    if mode == "real":
        return RealWechatAdapter(
            config.wechat_app_id,
            config.wechat_app_secret,
            default_thumb_path=config.wechat_default_thumb_path or None,
            managed_roots=managed_cover_roots(config),
            project_root=config.root,
        )
    if mode == "mock":
        return MockWechatAdapter()
    raise ValueError("WECHAT_MODE 仅支持 mock 或 real")
