"""抖音发布包模板（Round 35 / round_098，deferred，不真上传）。"""

from __future__ import annotations

from pathlib import Path

DOUYIN_PACK_VERSION = 1


def build_douyin_publish_pack(
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

    (dest / "douyin_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("douyin_title.txt")

    (dest / "douyin_caption.txt").write_text(
        (caption + "\n") if caption else "（文案为空）\n",
        encoding="utf-8",
    )
    written.append("douyin_caption.txt")

    (dest / "douyin_body_supplement.md").write_text(
        "\n".join(
            [
                "# 备稿（可选）",
                "",
                body_text or "（正文为空）",
                "",
                "抖音以短视频为主，长文仅作剪辑脚本参考。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("douyin_body_supplement.md")

    cover_note = "封面帧可用 cover.*" if has_cover else "请准备竖版封面/首帧"
    (dest / "douyin_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("douyin_cover_notes.txt")

    (dest / "douyin_video_placeholder.txt").write_text(
        "\n".join(
            [
                "# 视频（需人工准备）",
                "",
                "本包不含视频。请放入 video.mp4 后在抖音创作者中心上传。",
                "高风控平台：禁止无人值守发布。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("douyin_video_placeholder.txt")

    (dest / "douyin_tags_hint.md").write_text(
        "# 话题建议\n\n#日常 #干货\n\n请按实际内容修改，避免违规导流。\n",
        encoding="utf-8",
    )
    written.append("douyin_tags_hint.md")

    (dest / "douyin_publish_checklist.md").write_text(
        "\n".join(
            [
                "# 抖音人工发布清单（deferred）",
                "",
                "- [ ] 登录创作者平台（用户自行）",
                "- [ ] 上传 video.mp4",
                "- [ ] 填写标题/文案",
                "- [ ] 设置封面与话题",
                "- [ ] 人工确认后发布",
                "- [ ] 提交 proof",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("douyin_publish_checklist.md")

    (dest / "douyin_publish.md").write_text(
        "\n".join(
            [
                "# 抖音发布包（预研 / deferred）",
                "",
                "评估：高风控，仅 manual_export + 人工上传。",
                f"**标题**：douyin_title.txt",
                f"**封面**：{cover_note}",
                "导出成功 ≠ 已发布。",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    written.append("douyin_publish.md")

    return written
