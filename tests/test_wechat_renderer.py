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
