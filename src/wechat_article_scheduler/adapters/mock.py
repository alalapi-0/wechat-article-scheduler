"""Mock 微信适配器：不发起网络请求。"""

from __future__ import annotations

import uuid

from wechat_article_scheduler.adapters.base import DraftOptions, DraftResult, WechatAdapter
from wechat_article_scheduler.publish_preview import render_for_publish


class MockWechatAdapter(WechatAdapter):
    """本地模拟草稿与发布，便于开发与测试。"""

    def create_draft(
        self,
        *,
        title: str,
        summary: str,
        body: str,
        cover_path: str | None = None,
        options: DraftOptions | None = None,
    ) -> DraftResult:
        media_id = f"mock_media_{uuid.uuid4().hex[:16]}"
        opts = options or DraftOptions()
        content_html = render_for_publish(title, body)
        return DraftResult(
            media_id=media_id,
            raw_response={
                "errcode": 0,
                "errmsg": "ok",
                "media_id": media_id,
                "mode": "mock",
                "title": title,
                "content": content_html,
                "cover_path": cover_path or "",
                "need_open_comment": opts.need_open_comment,
                "only_fans_can_comment": opts.only_fans_can_comment,
            },
        )

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
        opts = options or DraftOptions()
        content_html = render_for_publish(title, body)
        return DraftResult(
            media_id=media_id,
            raw_response={
                "errcode": 0,
                "errmsg": "ok",
                "media_id": media_id,
                "mode": "mock",
                "updated": True,
                "index": index,
                "title": title,
                "content": content_html,
                "cover_path": cover_path or "",
                "need_open_comment": opts.need_open_comment,
                "only_fans_can_comment": opts.only_fans_can_comment,
            },
        )

    def submit_publish(self, media_id: str, *, force: bool = False) -> dict:
        return {
            "errcode": 0,
            "errmsg": "ok",
            "publish_id": f"mock_pub_{uuid.uuid4().hex[:12]}",
            "media_id": media_id,
            "mode": "mock",
        }
