"""Mock 适配器与发布正文规范化（Round 48）。"""

from __future__ import annotations

from wechat_article_scheduler.adapters.mock import MockWechatAdapter


def test_mock_create_draft_strips_duplicate_title_in_content() -> None:
    adapter = MockWechatAdapter()
    result = adapter.create_draft(
        title="重复标题",
        summary="摘要",
        body="# 重复标题\n\n<p>正文</p>",
    )
    content = result.raw_response["content"]
    assert result.raw_response["title"] == "重复标题"
    assert "<h1" not in content.lower()
    assert "正文" in content
