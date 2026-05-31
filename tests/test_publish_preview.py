"""公众号效果预览（Round 49）。"""

from __future__ import annotations

from wechat_article_scheduler.publish_preview import (
    build_publish_preview,
    render_for_publish,
)


def test_build_publish_preview_strips_duplicate_title() -> None:
    out = build_publish_preview("重复", "摘要", "# 重复\n\n正文。")
    assert "<h1" not in out["html_body"].lower()
    assert "正文" in out["html_body"]
    assert out["raw_body"].startswith("# 重复")


def test_unescape_html_entities_before_render() -> None:
    body = "&lt;p&gt;段落&lt;/p&gt;"
    out = build_publish_preview("标题", "", body)
    assert "&lt;p&gt;" not in out["html_body"]
    assert "段落" in out["html_body"]


def test_render_for_publish_matches_preview_html() -> None:
    title, body = "文", "# 文\n\n内容"
    preview = build_publish_preview(title, "", body)
    assert render_for_publish(title, body) == preview["html_body"]
