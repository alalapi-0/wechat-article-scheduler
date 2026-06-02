"""快手发布包模板（Round 35 / round_098，deferred，不真上传）。"""

from __future__ import annotations

from pathlib import Path

KUAISHOU_PACK_VERSION = 1


def build_kuaishou_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    written: list[str] = []
    title_line = (title or "").strip()
    caption = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "kuaishou_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("kuaishou_title.txt")

    (dest / "kuaishou_caption.txt").write_text(
        (caption + "\n") if caption else "（文案为空）\n",
        encoding="utf-8",
    )
    written.append("kuaishou_caption.txt")

    (dest / "kuaishou_body_supplement.md").write_text(
        "\n".join(["# 备稿", "", body_text or "（无）"]) + "\n",
        encoding="utf-8",
    )
    written.append("kuaishou_body_supplement.md")

    cover_note = "封面可用 cover.*" if has_cover else "请准备竖版封面"
    (dest / "kuaishou_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("kuaishou_cover_notes.txt")

    (dest / "kuaishou_video_placeholder.txt").write_text(
        "请自备 video.mp4，在快手创作者平台上传。本包不含视频。\n",
        encoding="utf-8",
    )
    written.append("kuaishou_video_placeholder.txt")

    (dest / "kuaishou_publish_checklist.md").write_text(
        "\n".join(
            [
                "# 快手人工发布清单（deferred）",
                "",
                "- [ ] 登录快手创作者平台",
                "- [ ] 上传视频",
                "- [ ] 填写标题与描述",
                "- [ ] 人工发布后提交 proof",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("kuaishou_publish_checklist.md")

    (dest / "kuaishou_publish.md").write_text(
        f"# 快手发布包（deferred）\n\n**标题**：kuaishou_title.txt\n**封面**：{cover_note}\n",
        encoding="utf-8",
    )
    written.append("kuaishou_publish.md")

    return written
