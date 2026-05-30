from wechat_article_scheduler.renderers import render_markdown_to_html


def test_markdown_paragraphs_render_with_margin_style() -> None:
    md = "第一段。\n\n第二段。"
    html = render_markdown_to_html(md)
    assert '<p style="margin: 0 0 1em;">第一段。</p>' in html
    assert '<p style="margin: 0 0 1em;">第二段。</p>' in html
