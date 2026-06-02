"""知乎发布包模板（Round 24 / round_079）。"""

from __future__ import annotations

from pathlib import Path

ZHIHU_PACK_VERSION = 1
# 知乎标题常见上限（待官方核验，仅作本地提示）
ZHIHU_TITLE_HINT_MAX = 100
ZHIHU_EXCERPT_HINT_MAX = 200


def build_zhihu_publish_pack(
    dest: Path,
    *,
    title: str,
    digest: str,
    body: str,
    has_cover: bool,
) -> list[str]:
    """写入知乎可复制字段文件，返回相对文件名列表。"""
    written: list[str] = []
    title_line = (title or "").strip()
    excerpt = (digest or "").strip()
    body_text = (body or "").strip()

    (dest / "zhihu_title.txt").write_text(title_line + "\n", encoding="utf-8")
    written.append("zhihu_title.txt")

    (dest / "zhihu_excerpt.txt").write_text(excerpt + "\n", encoding="utf-8")
    written.append("zhihu_excerpt.txt")

    body_md = f"{body_text}\n" if body_text else "（正文为空，请先完善作品）\n"
    (dest / "zhihu_body.md").write_text(body_md, encoding="utf-8")
    written.append("zhihu_body.md")

    cover_note = (
        "已包含 cover.*，请在知乎编辑器中上传为文章封面或头图。"
        if has_cover
        else "未检测到封面文件：建议在知乎后台单独上传封面图。"
    )
    (dest / "zhihu_cover_notes.txt").write_text(cover_note + "\n", encoding="utf-8")
    written.append("zhihu_cover_notes.txt")

    checklist = "\n".join(
        [
            "# 知乎发布清单",
            "",
            "- [ ] 登录知乎创作中心（本工具不会代登录）",
            "- [ ] 粘贴标题（见 `zhihu_title.txt`）",
            "- [ ] 粘贴导语/摘要（见 `zhihu_excerpt.txt`）",
            "- [ ] 粘贴正文（见 `zhihu_body.md` 或 `article.html`）",
            f"- [ ] 封面：{cover_note}",
            "- [ ] 选择话题/专栏（需人工判断）",
            "- [ ] 预览后手动点击发布",
            "- [ ] 回到本仓库作品详情提交 **发布证明（proof）**",
            "",
            "> 导出成功 ≠ 已发布；不得在未提交 proof 前将本地状态标为已发布。",
        ]
    )
    (dest / "zhihu_publish_checklist.md").write_text(checklist + "\n", encoding="utf-8")
    written.append("zhihu_publish_checklist.md")

    publish_doc = "\n".join(
        [
            "# 知乎发布包（一键复制参考）",
            "",
            f"**标题**（建议 ≤{ZHIHU_TITLE_HINT_MAX} 字）",
            "",
            "```",
            title_line,
            "```",
            "",
            f"**导语/摘要**（建议 ≤{ZHIHU_EXCERPT_HINT_MAX} 字）",
            "",
            "```",
            excerpt,
            "```",
            "",
            "**正文**",
            "",
            "见 `zhihu_body.md`；富文本场景可复制 `article.html` 中渲染结果。",
            "",
            "**封面**",
            "",
            cover_note,
            "",
            "详见 `zhihu_publish_checklist.md`。",
        ]
    )
    (dest / "zhihu_publish.md").write_text(publish_doc + "\n", encoding="utf-8")
    written.append("zhihu_publish.md")

    return written
