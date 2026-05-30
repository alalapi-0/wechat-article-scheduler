"""微信 API 适配器工厂。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.base import WechatAdapter
from wechat_article_scheduler.adapters.mock import MockWechatAdapter
from wechat_article_scheduler.adapters.real import RealWechatAdapter
from wechat_article_scheduler.config import AppConfig


def get_adapter(config: AppConfig) -> WechatAdapter:
    """根据 WECHAT_MODE 返回适配器（默认 mock）。"""
    mode = (config.wechat_mode or "mock").lower()
    if mode == "real":
        return RealWechatAdapter(
            config.wechat_app_id,
            config.wechat_app_secret,
            default_thumb_path=config.wechat_default_thumb_path or None,
            enable_publish=config.wechat_enable_publish,
        )
    return MockWechatAdapter()
