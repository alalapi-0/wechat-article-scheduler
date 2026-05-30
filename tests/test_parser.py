from pathlib import Path

from wechat_article_scheduler.parser import parse_file, content_hash, make_summary


def test_parse_markdown_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "post.md"
    p.write_text(
        "---\ntitle: 测试标题\nsummary: 简短摘要\n---\n\n# 忽略\n\n正文第一段。",
        encoding="utf-8",
    )
    art = parse_file(p)
    assert art.title == "测试标题"
    assert art.summary == "简短摘要"
    assert "正文" in art.body
    assert len(art.content_hash) == 64


def test_content_hash_stable() -> None:
    h1 = content_hash("Hello", "World")
    h2 = content_hash("hello", "World")
    assert h1 == h2


def test_make_summary_truncates() -> None:
    long_body = "字" * 300
    s = make_summary(long_body, max_chars=50)
    assert len(s) <= 51
