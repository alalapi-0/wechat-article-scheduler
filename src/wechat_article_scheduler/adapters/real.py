"""真实微信公众平台 API 适配器（仅 WECHAT_MODE=real 且凭证齐全时启用）。"""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
from typing import Any, Callable

from wechat_article_scheduler.adapters.base import DraftOptions, DraftResult, WechatAdapter
from wechat_article_scheduler.adapters.wechat_http import (
    API_BASE,
    TokenCache,
    WechatApiError,
    http_get_json,
    http_post_json,
    http_post_multipart,
    redact_url,
)
from wechat_article_scheduler.cover_assets.index import (
    InvalidCoverError,
    inspect_cover_path,
    secure_cover_bytes,
)
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_preview import render_for_publish

logger = logging.getLogger(__name__)


class RealWechatAdapter(WechatAdapter):
    """
    真实微信草稿适配器。

    流程：获取 access_token → 上传封面 thumb → draft/add/draft/update。
    网络调用可注入 http_get/post 便于单元测试 mock。
    """

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        default_thumb_path: str | None = None,
        managed_roots: tuple[Path, ...] | None = None,
        project_root: Path | None = None,
        token_cache: TokenCache | None = None,
        http_get: Callable[..., dict[str, Any]] | None = None,
        http_post_json_fn: Callable[..., dict[str, Any]] | None = None,
        http_post_multipart_fn: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._default_thumb_path = default_thumb_path
        self._managed_roots = managed_roots
        self._project_root = project_root
        self._token_cache = token_cache or TokenCache()
        self._http_get = http_get or http_get_json
        self._http_post_json = http_post_json_fn or http_post_json
        self._http_post_multipart = http_post_multipart_fn or http_post_multipart
        self._thumb_cache_by_path: dict[str, str] = {}
        self._last_thumb_digest: str | None = None

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

    def _resolve_thumb_path(self, cover_path: str | None) -> str:
        """选择并校验 JPG/JPEG/PNG 文章封面或默认封面。"""
        chosen = (cover_path or "").strip()
        if chosen:
            if self._managed_roots is None:
                raise RuntimeError("文章封面缺少明确的受管目录，已拒绝读取")
            candidate = Path(chosen)
            if not candidate.is_absolute():
                if self._project_root is None:
                    raise RuntimeError("相对封面路径缺少项目根目录，已拒绝读取")
                candidate = self._project_root / candidate
            try:
                secure_cover_bytes(candidate, allowed_roots=self._managed_roots)
            except InvalidCoverError as exc:
                raise RuntimeError(str(exc)) from exc
            check = inspect_cover_path(candidate)
        else:
            check = inspect_cover_path(self._default_thumb_path)
        if not check["ok"]:
            raise RuntimeError(str(check["message"]))
        return str(check["resolved_path"])

    def _load_thumb_bytes(self, thumb_path: str, *, using_default: bool) -> bytes:
        """读取已解析的非空封面；读取失败时在联网前拒绝。"""
        try:
            roots = (
                (Path(thumb_path).parent,)
                if using_default or self._managed_roots is None
                else self._managed_roots
            )
            thumb_bytes = secure_cover_bytes(Path(thumb_path), allowed_roots=roots)
        except (OSError, InvalidCoverError) as exc:
            raise RuntimeError(f"封面文件无法读取：{thumb_path}") from exc
        if not thumb_bytes:
            raise RuntimeError(f"封面文件为空：{thumb_path}")
        return thumb_bytes

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

        按封面路径缓存 media_id，避免重复上传；未指定单篇封面时使用有效默认封面。
        """
        thumb_path = self._resolve_thumb_path(cover_path)
        thumb_bytes = self._load_thumb_bytes(thumb_path, using_default=not bool((cover_path or "").strip()))
        cache_key = hashlib.sha256(thumb_bytes).hexdigest()
        self._last_thumb_digest = cache_key
        if cache_key in self._thumb_cache_by_path:
            return self._thumb_cache_by_path[cache_key]
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/material/add_material?access_token={token}&type=thumb"
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
        return media_id

    def create_draft(
        self,
        *,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None = None,
        options: DraftOptions | None = None,
    ) -> DraftResult:
        """调用 draft/add 创建草稿。"""
        self._ensure_credentials()
        opts = options or DraftOptions()
        article = self._build_article_fields(
            title=title,
            summary=summary,
            body=body,
            cover_path=cover_path,
            options=opts,
        )
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/draft/add?access_token={token}"
        payload = {"articles": [article]}
        logger.info("创建草稿: title=%r", title[:80])
        data = self._http_post_json(url, payload)
        media_id = str(data.get("media_id", ""))
        if not media_id:
            raise WechatApiError(-1, "draft media_id 缺失", endpoint="draft/add")
        raw = dict(data)
        raw["content_fingerprint"] = self._exact_content_fingerprint(
            title=title, summary=summary, body=body
        )
        return DraftResult(media_id=media_id, raw_response=raw)

    def _exact_content_fingerprint(self, *, title: str, summary: str, body: str) -> str:
        if self._last_thumb_digest is None:
            raise RuntimeError("封面内容身份缺失，已拒绝记录草稿")
        from wechat_article_scheduler.draft_update import (
            draft_content_fingerprint_from_cover_digest,
        )

        return draft_content_fingerprint_from_cover_digest(
            title=title,
            summary=summary,
            body=body,
            cover_digest=self._last_thumb_digest,
        )

    def _build_article_fields(
        self,
        *,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None,
        options: DraftOptions,
    ) -> dict[str, Any]:
        thumb_media_id = self.upload_thumb_media(cover_path)
        return {
            "title": title,
            "author": options.author or "",
            "digest": clamp_summary(summary or title, 120),
            "content": render_for_publish(title, body),
            "content_source_url": options.content_source_url or "",
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1 if options.need_open_comment else 0,
            "only_fans_can_comment": 1 if options.only_fans_can_comment else 0,
        }

    def update_draft(
        self,
        *,
        media_id: str,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None = None,
        options: DraftOptions | None = None,
        index: int = 0,
    ) -> DraftResult:
        """调用 draft/update 更新已有草稿（media_id 不变）。"""
        self._ensure_credentials()
        opts = options or DraftOptions()
        article = self._build_article_fields(
            title=title,
            summary=summary,
            body=body,
            cover_path=cover_path,
            options=opts,
        )
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/draft/update?access_token={token}"
        payload = {
            "media_id": media_id,
            "index": int(index),
            "articles": article,
        }
        logger.info("更新草稿: media_id=%s title=%r", media_id[:16], title[:80])
        data = self._http_post_json(url, payload)
        out_id = str(data.get("media_id") or media_id)
        raw = dict(data)
        raw["content_fingerprint"] = self._exact_content_fingerprint(
            title=title, summary=summary, body=body
        )
        return DraftResult(media_id=out_id, raw_response=raw)

    def list_drafts_batchget(self, *, offset: int = 0, count: int = 20) -> dict:
        """调用 draft/batchget 分页获取草稿列表。"""
        self._ensure_credentials()
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/draft/batchget?access_token={token}"
        logger.info("拉取远端草稿列表 offset=%s count=%s", offset, count)
        return self._http_post_json(url, {"offset": int(offset), "count": int(count), "no_content": 0})

    def list_published_batchget(self, *, offset: int = 0, count: int = 20) -> dict:
        """调用 freepublish/batchget 分页获取已发布列表。"""
        self._ensure_credentials()
        token = self.get_access_token()
        url = f"{API_BASE}/cgi-bin/freepublish/batchget?access_token={token}"
        logger.info("拉取已发布列表 offset=%s count=%s", offset, count)
        return self._http_post_json(url, {"offset": int(offset), "count": int(count), "no_content": 1})
