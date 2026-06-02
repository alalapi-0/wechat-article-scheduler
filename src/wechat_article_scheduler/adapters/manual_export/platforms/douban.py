"""豆瓣发布包模板（Round 26 / round_080）。"""

from __future__ import annotations

from pathlib import Path

DOUBAN_PACK_VERSION = 1


def build_douban_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    written: list[str] = []
    title_line = (title or "").strip()
    excerpt = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "douban_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("douban_title.txt")

    (dest / "douban_intro.txt").write_text(excerpt + "\n", encoding="utf-8")
    written.append("douban_intro.txt")

    (dest / "douban_body.md").write_text(
        (body_text + "\n") if body_text else "（正文为空）\n",
        encoding="utf-8",
    )
    written.append("douban_body.md")

    tags_hint = "\n".join(
        [
            "# 豆瓣标签提示",
            "",
            "豆瓣标签需人工选择，以下为建议（可自行增删）：",
            "",
            "- 随笔",
            "- 书评",
            "- 日记",
            "",
            f"导语参考：`douban_intro.txt`",
        ]
    )
    (dest / "douban_tags_hint.md").write_text(tags_hint + "\n", encoding="utf-8")
    written.append("douban_tags_hint.md")

    cover_note = "使用 cover.* 作为头图" if has_cover else "请单独准备封面/配图"
    (dest / "douban_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("douban_cover_notes.txt")

    (dest / "douban_publish.md").write_text(
        "\n".join(
            [
                "# 豆瓣发布包",
                "",
                f"**标题**：见 `douban_title.txt`",
                "",
                f"**正文**：见 `douban_body.md`",
                "",
                f"**封面**：{cover_note}",
                "",
                "发布后在作品详情提交 proof。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("douban_publish.md")

    return written
