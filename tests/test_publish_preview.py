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


def test_publish_preview_preserves_embedded_html_blocks() -> None:
    body = (
        "# 标题\n"
        "## 小节\n"
        "<p style=\"font-size:0.72em;\">说明</p>\n\n"
        "正文"
    )
    out = build_publish_preview("标题", "", body)
    assert "小节" in out["html_body"]
    assert "font-size: 22px" in out["html_body"]
    assert "font-size: 13px" in out["html_body"]
    assert "说明" in out["html_body"]
    assert "##" not in out["html_body"]
    assert "&lt;p" not in out["html_body"]


def test_render_for_publish_outputs_wechat_compatible_html() -> None:
    body = (
        "# 001　是谁杀死了勇者\n"
        "## 序章\n"
        '<p style="font-size:0.72em;color:#888;">原文：<a href="https://example.com">链接</a></p>\n\n'
        "正文。"
    )
    html = render_for_publish("001　是谁杀死了勇者", body)
    assert "##" not in html
    assert "&lt;p" not in html
    assert '<a href="https://example.com">链接</a>' in html
    assert "序章" in html
    assert "正文。" in html


def test_render_for_publish_matches_preview_html() -> None:
    title, body = "文", "# 文\n\n内容"
    preview = build_publish_preview(title, "", body)
    assert render_for_publish(title, body) == preview["html_body"]
