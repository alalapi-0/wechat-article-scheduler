"""Markdown 到微信 HTML 的渲染器（Round 13 深化）。"""

from __future__ import annotations

import html
import re

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
_LIST_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _inline_markup(text: str) -> str:
    """转义后处理行内链接与图片占位。"""
    combined = re.compile(
        r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)"
    )
    out: list[str] = []
    pos = 0
    for match in combined.finditer(text):
        if match.start() > pos:
            out.append(html.escape(text[pos : match.start()]))
        if match.group(0).startswith("!"):
            alt = html.escape(match.group(1) or "图片")
            url = html.escape(match.group(2))
            out.append(f'<span class="img-placeholder" title="{url}">[{alt}]</span>')
        else:
            label = html.escape(match.group(3))
            href = html.escape(match.group(4), quote=True)
            out.append(f'<a href="{href}">{label}</a>')
        pos = match.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _render_block(block: str) -> str:
    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    if not lines:
        return ""

    if len(lines) == 1:
        m = _HEADING_RE.match(lines[0])
        if m:
            level = len(m.group(1))
            tag = f"h{level}"
            return f"<{tag} style=\"margin: 0 0 0.75em;\">{_inline_markup(m.group(2))}</{tag}>"

    if all(_LIST_ITEM_RE.match(ln) for ln in lines):
        items = "".join(
            f"<li style=\"margin: 0 0 0.35em;\">{_inline_markup(_LIST_ITEM_RE.match(ln).group(1))}</li>"
            for ln in lines
        )
        return f'<ul style="margin: 0 0 1em; padding-left: 1.25em;">{items}</ul>'

    if len(lines) == 1:
        return f'<p style="margin: 0 0 1em;">{_inline_markup(lines[0])}</p>'

    inner = "<br/>".join(_inline_markup(ln) for ln in lines)
    return f'<p style="margin: 0 0 1em;">{inner}</p>'


def render_markdown_to_html(markdown_text: str) -> str:
    """
    将 Markdown 文本渲染为 HTML。

    支持：段落、# 标题（1–3 级）、列表、链接、图片占位；已是 HTML 时原样返回。
    """
    raw = markdown_text or ""
    stripped = raw.lstrip()
    if stripped.startswith("<"):
        return raw

    blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
    if not blocks:
        return ""
    return "\n".join(_render_block(b) for b in blocks)


def render_markdown_to_html_safe(markdown_text: str) -> tuple[str, str | None]:
    """渲染并在失败时降级为转义段落。"""
    try:
        return render_markdown_to_html(markdown_text), None
    except Exception as exc:  # noqa: BLE001 — 预览路径需兜底
        safe = html.escape((markdown_text or "").strip())
        fallback = f'<p style="margin: 0 0 1em;">{safe}</p>' if safe else ""
        return fallback, str(exc)
