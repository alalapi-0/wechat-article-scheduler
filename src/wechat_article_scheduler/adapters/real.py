"""真实微信公众平台 API 适配器（仅 WECHAT_MODE=real 且凭证齐全时启用）。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from wechat_article_scheduler.adapters.base import DraftResult, WechatAdapter
from wechat_article_scheduler.adapters.wechat_http import (
    API_BASE,
    TokenCache,
    WechatApiError,
    http_get_json,
    http_post_json,
    http_post_multipart,
    redact_url,
)
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.renderers import render_markdown_to_html

logger = logging.getLogger(__name__)

# 最小 1x1 PNG，用于未配置封面时的占位 thumb 上传
_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class RealWechatAdapter(WechatAdapter):
    """
    真实微信草稿/发布适配器。

    流程：获取 access_token → 上传封面 thumb → draft/add → freepublish/submit。
    网络调用可注入 http_get/post 便于单元测试 mock。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        default_thumb_path: str | None = None,
        enable_publish: bool = True,
        token_cache: TokenCache | None = None,
        http_get: Callable[..., dict[str, Any]] | None = None,
        http_post_json_fn: Callable[..., dict[str, Any]] | None = None,
        http_post_multipart_fn: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._default_thumb_path = default_thumb_path
        self._enable_publish = enable_publish
        self._token_cache = token_cache or TokenCache()
        self._http_get = http_get or http_get_json
        self._http_post_json = http_post_json_fn or http_post_json
        self._http_post_multipart = http_post_multipart_fn or http_post_multipart
        self._cached_thumb_media_id: str | None = None
        self._thumb_cache_by_path: dict[str, str] = {}

    def _ensure_credentials(self) -> None:
        if not self._app_id or not self._app_secret:
            raise RuntimeError("WECHAT_APP_ID / WECHAT_APP_SECRET 未配置，无法使用 real 模式")

    def build_token_request_url(self) -> str:
        """
        构造获取 access_token 的 URL（日志/调试用，secret 已脱敏）。

        文档：https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
        """
        self._ensure_credentials()
        return (
            "https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential&appid={self._app_id}&secret=***REDACTED***"
        )

    def _fetch_access_token(self) -> dict[str, Any]:
        """向微信服务器请求新的 access_token。"""
        self._ensure_credentials()
        url = (
            f"{API_BASE}/cgi-bin/token"
            f"?grant_type=client_credential&appid={self._app_id}&secret={self._app_secret}"
        )
        logger.debug("请求 access_token: %s", redact_url(url, self._app_secret))
        return self._http_get(url)

    def get_access_token(self) -> str:
        """返回缓存或新刷新的 access_token（禁止写入日志）。"""
        return self._token_cache.get_token(self._fetch_access_token)

    def _resolve_thumb_path(self, cover_path: str | None) -> str | None:
        """选择封面：优先单篇 cover_path，回退全局默认封面。"""
        if cover_path and Path(cover_path).is_file():
            return cover_path
        if self._default_thumb_path and Path(self._default_thumb_path).is_file():
            return self._default_thumb_path
        return None

    def _load_thumb_bytes(self, thumb_path: str | None) -> bytes:
        """读取封面图字节；未配置时使用内置最小 PNG。"""
        if thumb_path:
            path = Path(thumb_path)
            if path.is_file():
                return path.read_bytes()
        return _MIN_PNG

    def _thumb_multipart_part(
        self, thumb_bytes: bytes, thumb_path: str | None
    ) -> tuple[str, bytes, str]:
        """根据路径或文件头返回 multipart 的 (filename, bytes, content_type)。"""
        if thumb_path:
            suffix = Path(thumb_path).suffix.lower()
            if suffix in (".jpg", ".jpeg"):
                return ("thumb.jpg", thumb_bytes, "image/jpeg")
            if suffix == ".png":
                return ("thumb.png", thumb_bytes, "image/png")
        if thumb_bytes[:3] == b"\xff\xd8\xff":
            return ("thumb.jpg", thumb_bytes, "image/jpeg")
        return ("thumb.png", thumb_bytes, "image/png")

    def upload_thumb_media(self, cover_path: str | None = None) -> str:
        """
        上传封面 thumb 素材，返回 media_id。

        按封面路径缓存 media_id，避免重复上传；未指定时使用全局默认封面/占位图。
        """
        thumb_path = self._resolve_thumb_path(cover_path)
        cache_key = thumb_path or "__default__"
        if cache_key in self._thumb_cache_by_path:
            return self._thumb_cache_by_path[cache_key]
        if thumb_path is None and self._cached_thumb_media_id:
            return self._cached_thumb_media_id
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/material/add_material?access_token={token}&type=thumb"
        thumb_bytes = self._load_thumb_bytes(thumb_path)
        filename, thumb_bytes, content_type = self._thumb_multipart_part(thumb_bytes, thumb_path)
        logger.info(
            "上传封面素材 thumb（%s，%d 字节）",
            content_type,
            len(thumb_bytes),
        )
        data = self._http_post_multipart(
            url,
            fields={},
            files={"media": (filename, thumb_bytes, content_type)},
        )
        media_id = str(data.get("media_id", ""))
        if not media_id:
            raise WechatApiError(-1, "thumb media_id 缺失", endpoint="material/add_material")
        self._thumb_cache_by_path[cache_key] = media_id
        if thumb_path is None:
            self._cached_thumb_media_id = media_id
        return media_id

    def create_draft(
        self, *, title: str, summary: str, body: str, cover_path: str | None = None
    ) -> DraftResult:
        """调用 draft/add 创建草稿。"""
        self._ensure_credentials()
        token = self.get_access_token()
        thumb_media_id = self.upload_thumb_media(cover_path)
        url = f"{API_BASE}/cgi-bin/draft/add?access_token={token}"
        payload = {
            "articles": [
                {
                    "title": title,
                    "author": "",
                    "digest": clamp_summary(summary or title, 120),
                    "content": render_markdown_to_html(publish_body_for(title, body)),
                    "content_source_url": "",
                    "thumb_media_id": thumb_media_id,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0,
                }
            ]
        }
        logger.info("创建草稿: title=%r", title[:80])
        data = self._http_post_json(url, payload)
        media_id = str(data.get("media_id", ""))
        if not media_id:
            raise WechatApiError(-1, "draft media_id 缺失", endpoint="draft/add")
        return DraftResult(media_id=media_id, raw_response=data)

    def submit_publish(self, media_id: str) -> dict:
        """调用 freepublish/submit 提交发布（可通过 enable_publish=False 跳过）。"""
        self._ensure_credentials()
        if not self._enable_publish:
            return {
                "errcode": 0,
                "errmsg": "ok",
                "skipped": True,
                "reason": "WECHAT_ENABLE_PUBLISH=false",
                "media_id": media_id,
            }
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/freepublish/submit?access_token={token}"
        logger.info("提交发布: media_id=%s", media_id[:16] + "...")
        return self._http_post_json(url, {"media_id": media_id})
