from pathlib import Path

from wechat_article_scheduler.parser import make_summary, parse_file
from wechat_article_scheduler.renderers import render_markdown_to_html, render_markdown_to_html_safe

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_article.md"


def test_markdown_paragraphs_render_with_margin_style() -> None:
    md = "第一段。\n\n第二段。"
    html = render_markdown_to_html(md)
    assert '<p style="margin: 0 0 1em;">第一段。</p>' in html
    assert '<p style="margin: 0 0 1em;">第二段。</p>' in html


def test_markdown_heading_list_link_image_fixture() -> None:
    md = FIXTURE.read_text(encoding="utf-8")
    html = render_markdown_to_html(md)
    assert "<h1" in html and "示例章节" in html
    assert "<ul" in html and "列表项一" in html
    assert '<a href="https://example.com">' in html
    assert "img-placeholder" in html


def test_markdown_mixed_with_html_blocks_renders_instead_of_escaping() -> None:
    md = (
        "# 标题\n"
        "## 小节\n"
        "<p style=\"color:#888;\">\n"
        "说明：<a href=\"https://example.com\">链接</a>\n"
        "</p>\n\n"
        "正文。"
    )
    html = render_markdown_to_html(md)
    assert "<h1" in html and "标题" in html
    assert "<h2" in html and "小节" in html
    assert '<p style="color:#888;">' in html
    assert '<a href="https://example.com">链接</a>' in html
    assert "&lt;p" not in html
    assert "&lt;a" not in html


def test_render_safe_returns_error_field_on_failure(monkeypatch) -> None:
    def boom(_text: str) -> str:
        raise ValueError("boom")

    monkeypatch.setattr(
        "wechat_article_scheduler.renderers.markdown.render_markdown_to_html",
        boom,
    )
    html, err = render_markdown_to_html_safe("你好")
    assert err == "boom"
    assert "你好" in html


def test_parse_file_title_summary_fallback(tmp_path: Path) -> None:
    p = tmp_path / "no_meta.md"
    p.write_text("# 章节标题\n\n正文内容。", encoding="utf-8")
    art = parse_file(p)
    assert art.title == "章节标题"
    assert art.summary


def test_make_summary_empty_body_fallback() -> None:
    assert make_summary("") == ""
