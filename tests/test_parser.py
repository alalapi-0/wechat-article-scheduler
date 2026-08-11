from pathlib import Path

import pytest

from wechat_article_scheduler.parser import parse_file, content_hash, make_summary
from wechat_article_scheduler.filesystem_safety import UnsafePathError


def test_parse_markdown_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "post.md"
    p.write_text(
        "---\ntitle: 测试标题\nsummary: 简短摘要\n---\n\n# 忽略\n\n正文第一段。",
        encoding="utf-8",
    )
    art = parse_file(p, allowed_roots=(tmp_path,))
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
    assert len(s) <= 50


def test_parse_file_rejects_symlink_and_hardlink(tmp_path: Path) -> None:
    original = tmp_path / "original.md"
    original.write_text("# secret", encoding="utf-8")
    symlink = tmp_path / "symlink.md"
    symlink.symlink_to(original)
    with pytest.raises(UnsafePathError):
        parse_file(symlink, allowed_roots=(tmp_path,))
    hardlink = tmp_path / "hardlink.md"
    hardlink.hardlink_to(original)
    with pytest.raises(UnsafePathError):
        parse_file(original, allowed_roots=(tmp_path,))
