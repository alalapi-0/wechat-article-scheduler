"""微信视频号发布包模板（Round 34 / round_096，不真上传）。"""

from __future__ import annotations

from pathlib import Path

WECHAT_CHANNELS_PACK_VERSION = 1


def build_wechat_channels_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    """生成视频号人工发布包；与公众号 API 分离，不含视频二进制。"""
    written: list[str] = []
    title_line = (title or "").strip()
    description = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "channels_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("channels_title.txt")

    (dest / "channels_description.txt").write_text(
        (description + "\n") if description else "（描述为空，请在视频号助手补充）\n",
        encoding="utf-8",
    )
    written.append("channels_description.txt")

    (dest / "channels_article_link_note.txt").write_text(
        "\n".join(
            [
                "# 与公众号文章关系说明",
                "",
                "视频号发布与微信公众号草稿/API 相互独立。",
                "若内容源自本地文章，可将公众号链接或摘要人工附在描述中；",
                "本调度器不会自动关联 media_id 或同步发表。",
                "",
                "备稿正文（可选）：",
                "",
                body_text or "（无）",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("channels_article_link_note.txt")

    cover_note = "封面可用 cover.*" if has_cover else "请准备竖版封面（建议 3:4 或 9:16）"
    (dest / "channels_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("channels_cover_notes.txt")

    (dest / "channels_video_placeholder.txt").write_text(
        "\n".join(
            [
                "# 视频文件（需人工准备）",
                "",
                "本包不包含视频。请在目录放入例如：",
                "",
                "  video.mp4",
                "",
                "在「微信视频号助手」或手机端上传。",
                "不得将未授权视频提交到 git 仓库。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("channels_video_placeholder.txt")

    checklist = "\n".join(
        [
            "# 微信视频号人工发布清单",
            "",
            "- [ ] 打开视频号助手 / 微信客户端（用户自行登录）",
            "- [ ] 上传视频（channels_video_placeholder.txt）",
            "- [ ] 填写标题（channels_title.txt）",
            "- [ ] 填写描述（channels_description.txt）",
            "- [ ] 设置封面（channels_cover_notes.txt）",
            "- [ ] 如需关联公众号，见 channels_article_link_note.txt",
            "- [ ] 预览后发表",
            "- [ ] 在本项目提交 proof（视频链接或截图）",
            "",
            "注意：视频号成功 ≠ 微信公众号已发布。",
        ]
    )
    (dest / "channels_publish_checklist.md").write_text(checklist + "\n", encoding="utf-8")
    written.append("channels_publish_checklist.md")

    (dest / "channels_publish.md").write_text(
        "\n".join(
            [
                "# 微信视频号发布包",
                "",
                f"**标题**：见 `channels_title.txt`",
                f"**描述**：见 `channels_description.txt`",
                f"**封面**：{cover_note}",
                "**视频**：用户自备 video.mp4",
                "",
                "与公众号 scan/plan 主线分离；导出成功 ≠ 已发布。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("channels_publish.md")

    return written
