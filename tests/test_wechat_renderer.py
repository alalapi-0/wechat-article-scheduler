"""微信公众号草稿最终 HTML 渲染测试。"""

from __future__ import annotations

from wechat_article_scheduler.renderers.wechat import render_wechat_html


def test_wechat_renderer_converts_markdown_and_embedded_html() -> None:
    body = (
        "## 序章\n"
        '<p style="font-size:0.72em;color:#888;">说明：<a href="https://example.com">原文</a></p>\n\n'
        "正文第一段。"
    )
    html = render_wechat_html(body)
    assert "##" not in html
    assert "&lt;p" not in html
    assert "序章" in html
    assert "font-size: 22px" in html
    assert "font-size: 13px" in html
    assert '<a href="https://example.com">原文</a>' in html
    assert "正文第一段。" in html


def test_wechat_renderer_turns_spacer_html_into_break() -> None:
    html = render_wechat_html('<p style="margin:0.6em 0;line-height:0;font-size:0;">&nbsp;</p>')
    assert "&lt;p" not in html
    assert "<br/>" in html


def test_wechat_renderer_blockquote_ordered_code_bold() -> None:
    from pathlib import Path

    md = (Path(__file__).parent / "fixtures" / "wechat_render_round4.md").read_text(
        encoding="utf-8"
    )
    html = render_wechat_html(md)
    assert "引用一行" in html
    assert "border-left: 3px solid" in html
    assert "<ol" in html and "有序一" in html
    assert "<ul" in html and "无序 A" in html
    assert "<strong>粗体</strong>" in html
    assert "<em>斜体</em>" in html
    assert "code line" in html and "Menlo" in html
    assert "正文收尾" in html


def test_render_for_publish_same_as_preview_html() -> None:
    from wechat_article_scheduler.publish_preview import (
        build_publish_preview,
        render_for_publish,
    )

    title, body = "章", "# 章\n\n**重点**"
    assert render_for_publish(title, body) == build_publish_preview(title, "", body)["html_body"]
