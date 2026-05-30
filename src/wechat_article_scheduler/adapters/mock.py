"""Mock 微信适配器：不发起网络请求。"""

from __future__ import annotations

import uuid

from wechat_article_scheduler.adapters.base import DraftResult, WechatAdapter


class MockWechatAdapter(WechatAdapter):
    """本地模拟草稿与发布，便于开发与测试。"""

    def create_draft(self, *, title: str, summary: str, body: str) -> DraftResult:
        media_id = f"mock_media_{uuid.uuid4().hex[:16]}"
        return DraftResult(
            media_id=media_id,
            raw_response={"errcode": 0, "errmsg": "ok", "media_id": media_id, "mode": "mock"},
        )

    def submit_publish(self, media_id: str) -> dict:
        return {
            "errcode": 0,
            "errmsg": "ok",
            "publish_id": f"mock_pub_{uuid.uuid4().hex[:12]}",
            "media_id": media_id,
            "mode": "mock",
        }
