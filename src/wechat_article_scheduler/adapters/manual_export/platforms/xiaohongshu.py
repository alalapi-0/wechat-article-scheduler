"""小红书发布包模板（Round 32 / round_094，不真上传）。"""

from __future__ import annotations

from pathlib import Path

XHS_PACK_VERSION = 1


def build_xiaohongshu_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    """生成小红书图文/笔记人工发布包；图片与视频需用户自行准备。"""
    written: list[str] = []
    title_line = (title or "").strip()
    caption = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "xhs_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("xhs_title.txt")

    note_body = body_text or caption or "（正文为空）"
    (dest / "xhs_note_body.md").write_text(
        "\n".join(
            [
                "# 笔记正文",
                "",
                "小红书以短图文为主，可将下列内容作为笔记描述：",
                "",
                caption,
                "",
                "---",
                "",
                body_text or "",
            ]
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    written.append("xhs_note_body.md")

    (dest / "xhs_caption.txt").write_text(
        (caption + "\n") if caption else "（导语为空，请在上传页补充）\n",
        encoding="utf-8",
    )
    written.append("xhs_caption.txt")

    tags_hint = "\n".join(
        [
            "# 小红书话题与标签提示",
            "",
            "话题需在发布页人工添加，以下为占位建议：",
            "",
            "#生活记录",
            "#干货分享",
            "",
            "遵守社区规范，避免违规营销与导流表述。",
        ]
    )
    (dest / "xhs_tags_hint.md").write_text(tags_hint + "\n", encoding="utf-8")
    written.append("xhs_tags_hint.md")

    cover_note = "首张图可用 cover.*" if has_cover else "请准备 3:4 或 1:1 封面图（建议 1080px 宽）"
    (dest / "xhs_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("xhs_cover_notes.txt")

    (dest / "xhs_media_placeholder.txt").write_text(
        "\n".join(
            [
                "# 图片/视频素材（需人工准备）",
                "",
                "本包不包含图片或视频二进制。建议：",
                "",
                "- 图文笔记：在本目录放入 image_01.jpg … image_n.jpg",
                "- 视频笔记：放入 video.mp4 + 封面",
                "",
                "上传时在创作者中心选择素材。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("xhs_media_placeholder.txt")

    checklist = "\n".join(
        [
            "# 小红书人工发布清单",
            "",
            "- [ ] 登录创作者中心 / App（用户自行操作）",
            "- [ ] 选择「发布图文」或「发布视频」",
            "- [ ] 上传图片/视频（见 xhs_media_placeholder.txt）",
            "- [ ] 填写标题（xhs_title.txt）",
            "- [ ] 填写正文/描述（xhs_note_body.md / xhs_caption.txt）",
            "- [ ] 添加话题（xhs_tags_hint.md）",
            "- [ ] 设置封面（xhs_cover_notes.txt）",
            "- [ ] 预览后发布",
            "- [ ] 在本项目提交 proof（笔记链接或截图）",
        ]
    )
    (dest / "xhs_publish_checklist.md").write_text(checklist + "\n", encoding="utf-8")
    written.append("xhs_publish_checklist.md")

    (dest / "xhs_publish.md").write_text(
        "\n".join(
            [
                "# 小红书发布包",
                "",
                f"**标题**：见 `xhs_title.txt`",
                f"**描述**：见 `xhs_caption.txt` / `xhs_note_body.md`",
                f"**封面/首图**：{cover_note}",
                "**素材**：用户自备图片或视频",
                "",
                "高风控平台：仅人工路径。导出成功 ≠ 已发布。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("xhs_publish.md")

    return written
