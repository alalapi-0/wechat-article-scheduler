"""Mock 微信适配器：不发起网络请求。"""

from __future__ import annotations

import uuid

from wechat_article_scheduler.adapters.base import DraftOptions, DraftResult, WechatAdapter
from wechat_article_scheduler.publish_preview import render_for_publish


class MockWechatAdapter(WechatAdapter):
    """本地模拟草稿与发布，便于开发与测试。"""

    _MOCK_REMOTE_DRAFTS: tuple[dict, ...] = (
        {"media_id": "mock_remote_draft_001", "title": "[演练] 远端草稿 1", "update_time": 1700000001},
        {"media_id": "mock_remote_draft_002", "title": "[演练] 远端草稿 2", "update_time": 1700000002},
        {"media_id": "mock_remote_draft_003", "title": "[演练] 远端草稿 3", "update_time": 1700000003},
        {"media_id": "mock_remote_draft_004", "title": "[演练] 远端草稿 4", "update_time": 1700000004},
        {"media_id": "mock_remote_draft_005", "title": "[演练] 远端草稿 5", "update_time": 1700000005},
    )

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
        if not force:
            return {
                "errcode": 0,
                "errmsg": "ok",
                "skipped": True,
                "reason": "draft_only",
                "media_id": media_id,
                "mode": "mock",
            }
        return {
            "errcode": 0,
            "errmsg": "ok",
            "publish_id": f"mock_pub_{uuid.uuid4().hex[:12]}",
            "media_id": media_id,
            "mode": "mock",
        }

    def list_drafts_batchget(self, *, offset: int = 0, count: int = 20) -> dict:
        items = []
        for spec in self._MOCK_REMOTE_DRAFTS[offset : offset + count]:
            items.append(
                {
                    "media_id": spec["media_id"],
                    "update_time": spec["update_time"],
                    "content": {
                        "news_item": [{"title": spec["title"], "author": "", "digest": ""}],
                    },
                }
            )
        return {
            "errcode": 0,
            "errmsg": "ok",
            "total_count": len(self._MOCK_REMOTE_DRAFTS),
            "item_count": len(items),
            "item": items,
            "mode": "mock",
        }

    def list_published_batchget(self, *, offset: int = 0, count: int = 20) -> dict:
        return {
            "errcode": 48001,
            "errmsg": "api unauthorized",
            "mode": "mock",
        }

    def delete_draft(self, media_id: str) -> dict:
        return {"errcode": 0, "errmsg": "ok", "media_id": media_id, "mode": "mock"}
