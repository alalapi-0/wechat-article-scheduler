"""Markdown 到微信 HTML 的最小渲染器骨架。"""

from __future__ import annotations

import html


def render_markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 文本按段落渲染为 HTML。

    仅提供治理轮最小骨架：每个非空段落映射为带 margin 的 <p>。
    已是 HTML 的正文原样返回，避免影响现有行为。
    """
    raw = markdown_text or ""
    stripped = raw.lstrip()
    if stripped.startswith("<"):
        return raw

    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    return "\n".join(f'<p style="margin: 0 0 1em;">{html.escape(p)}</p>' for p in paragraphs)
