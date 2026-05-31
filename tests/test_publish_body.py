"""发布正文规范化测试（Round 48）。"""

from __future__ import annotations

from wechat_article_scheduler.publish_body import publish_body_for


def test_markdown_strips_duplicate_h1() -> None:
    body = "# 我的标题\n\n正文段落。"
    out = publish_body_for("我的标题", body)
    assert out.startswith("正文段落")
    assert "# 我的标题" not in out


def test_markdown_keeps_different_heading() -> None:
    body = "# 另一节\n\n内容。"
    out = publish_body_for("文章标题", body)
    assert out == body


def test_html_strips_duplicate_h1() -> None:
    body = "<h1>文章标题</h1><p>正文</p>"
    out = publish_body_for("文章标题", body)
    assert "<h1>" not in out
    assert "正文" in out


def test_title_match_is_case_and_space_insensitive() -> None:
    body = "#  Hello   World \n\n段落"
    out = publish_body_for("hello world", body)
    assert out.strip() == "段落"
