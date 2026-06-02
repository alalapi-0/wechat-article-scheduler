"""Bilibili 人工上传包模板（Round 30 / round_092，不真上传）。"""

from __future__ import annotations

from pathlib import Path

BILIBILI_PACK_VERSION = 1


def build_bilibili_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    """生成 Bilibili 上传所需文本与清单；视频文件需用户自行放入目录。"""
    written: list[str] = []
    title_line = (title or "").strip()
    description = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "bilibili_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("bilibili_title.txt")

    (dest / "bilibili_description.txt").write_text(
        (description + "\n") if description else "（简介为空，请在上传页补充）\n",
        encoding="utf-8",
    )
    written.append("bilibili_description.txt")

    (dest / "bilibili_body_supplement.md").write_text(
        "\n".join(
            [
                "# 正文补充（可选）",
                "",
                "B 站简介有字数限制，长文可截取要点放入简介，或保留本文件作备稿：",
                "",
                body_text or "（正文为空）",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("bilibili_body_supplement.md")

    tags_hint = "\n".join(
        [
            "# Bilibili 分区与标签提示",
            "",
            "分区、标签需在上传页人工选择，以下为占位建议：",
            "",
            "- 分区：知识 / 科技 / 生活（按实际内容修改）",
            "- 标签：建议 3–5 个，与标题主题相关",
            "",
            "勿自动刷标签；遵守社区规范。",
        ]
    )
    (dest / "bilibili_tags_hint.md").write_text(tags_hint + "\n", encoding="utf-8")
    written.append("bilibili_tags_hint.md")

    cover_note = "将 cover.* 用作视频封面" if has_cover else "请单独准备视频封面图（16:9 推荐）"
    (dest / "bilibili_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("bilibili_cover_notes.txt")

    (dest / "bilibili_video_placeholder.txt").write_text(
        "\n".join(
            [
                "# 视频文件（需人工准备）",
                "",
                "本导出包不包含视频二进制。请在本目录放入主视频，例如：",
                "",
                "  video.mp4",
                "",
                "上传时在 B 站创作中心选择该文件。",
                "禁止将未授权/超大文件误提交到仓库。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("bilibili_video_placeholder.txt")

    checklist = "\n".join(
        [
            "# Bilibili 人工上传清单",
            "",
            "- [ ] 登录 bilibili.com 创作中心",
            "- [ ] 选择视频文件（见 bilibili_video_placeholder.txt）",
            "- [ ] 填写标题（bilibili_title.txt）",
            "- [ ] 填写简介（bilibili_description.txt）",
            "- [ ] 上传封面（bilibili_cover_notes.txt）",
            "- [ ] 选择分区与标签（bilibili_tags_hint.md）",
            "- [ ] 预览后提交审核/发布",
            "- [ ] 在本项目作品详情提交 proof（链接或截图）",
        ]
    )
    (dest / "bilibili_upload_checklist.md").write_text(checklist + "\n", encoding="utf-8")
    written.append("bilibili_upload_checklist.md")

    (dest / "bilibili_publish.md").write_text(
        "\n".join(
            [
                "# Bilibili 发布包",
                "",
                f"**标题**：见 `bilibili_title.txt`",
                f"**简介**：见 `bilibili_description.txt`",
                f"**封面**：{cover_note}",
                "**视频**：用户自备 `video.mp4`（见 placeholder 说明）",
                "",
                "导出成功 ≠ 已发布。上传后提交 proof。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("bilibili_publish.md")

    return written
