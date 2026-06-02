"""微信公众号草稿正文 HTML 渲染。

微信草稿接口接收 HTML，但编辑器对 Markdown、转义 HTML 与部分块级标签比较挑剔。
这里把 Markdown/混合 HTML 统一转换成保守的内联样式 HTML，再交给 draft/add。
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_LIST_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
_ORDERED_LIST_RE = re.compile(r"^\d+\.\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_FENCE_RE = re.compile(r"^```(\w*)?\s*$")
_INLINE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_HTML_START_RE = re.compile(r"^\s*<([a-zA-Z][\w:-]*)\b")

_P_STYLE = "margin: 0 0 1em; line-height: 1.8; font-size: 16px; color: #222;"
_NOTE_STYLE = "margin: 0 0 1em; line-height: 1.6; font-size: 13px; color: #888;"
_SPACER_STYLE = "margin: 0 0 1em; line-height: 1.6; font-size: 16px;"
_H2_STYLE = "margin: 0 0 0.9em; line-height: 1.35; font-size: 22px; font-weight: 700; color: #111;"
_H3_STYLE = "margin: 0 0 0.75em; line-height: 1.4; font-size: 18px; font-weight: 700; color: #111;"
_LI_STYLE = "margin: 0 0 0.45em; line-height: 1.8; font-size: 16px; color: #222;"
_QUOTE_STYLE = (
    "margin: 0 0 1em; padding: 0.6em 0.9em; line-height: 1.7; font-size: 15px; "
    "color: #555; border-left: 3px solid #ddd;"
)
_CODE_STYLE = (
    "margin: 0 0 1em; padding: 0.75em; line-height: 1.5; font-size: 14px; "
    "font-family: Menlo, Consolas, monospace; color: #333; background: #f6f6f6;"
)


class _InlineHTMLToWechat(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            href = ""
            for key, value in attrs:
                if key.lower() == "href" and value:
                    href = value
                    break
            if href:
                self.parts.append(f'<a href="{html.escape(href, quote=True)}">')

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self.parts.append("</a>")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.escape(data))

    def handle_entityref(self, name: str) -> None:
        if name == "nbsp":
            self.parts.append("&nbsp;")
        else:
            self.parts.append(html.escape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.parts.append(html.escape(f"&#{name};"))

    def html(self) -> str:
        return "".join(self.parts)


def _apply_bold_italic(text: str) -> str:
    """先处理粗体/斜体，再交给链接与转义逻辑。"""
    parts: list[str] = []
    pos = 0
    for match in _BOLD_RE.finditer(text):
        if match.start() > pos:
            parts.append(_apply_italic_only(text[pos : match.start()]))
        parts.append(f"<strong>{html.escape(match.group(1))}</strong>")
        pos = match.end()
    parts.append(_apply_italic_only(text[pos:]))
    return "".join(parts)


def _apply_italic_only(text: str) -> str:
    out: list[str] = []
    pos = 0
    for match in _ITALIC_RE.finditer(text):
        if match.start() > pos:
            out.append(html.escape(text[pos : match.start()]))
        out.append(f"<em>{html.escape(match.group(1))}</em>")
        pos = match.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _inline_markdown(text: str) -> str:
    base = _apply_bold_italic(text)
    out: list[str] = []
    pos = 0
    for match in _INLINE_RE.finditer(base):
        if match.start() > pos:
            out.append(base[pos : match.start()])
        if match.group(0).startswith("!"):
            alt = html.escape(match.group(1) or "图片")
            out.append(f'<span style="color:#888;">[{alt}]</span>')
        else:
            label = match.group(3)
            if "<" not in label and ">" not in label:
                label = html.escape(label)
            href = html.escape(match.group(4), quote=True)
            out.append(f'<a href="{href}">{label}</a>')
        pos = match.end()
    out.append(base[pos:])
    return "".join(out)


def _strip_outer_block_tag(raw: str) -> tuple[str | None, str]:
    text = raw.strip()
    match = _HTML_START_RE.match(text)
    if not match:
        return None, raw
    tag = match.group(1).lower()
    close = re.search(rf"</{re.escape(tag)}>\s*$", text, flags=re.IGNORECASE | re.DOTALL)
    if not close:
        return tag, raw
    start_end = text.find(">")
    if start_end < 0:
        return tag, raw
    return tag, text[start_end + 1 : close.start()]


def _html_fragment_to_inline(raw: str) -> str:
    _tag, inner = _strip_outer_block_tag(raw)
    parser = _InlineHTMLToWechat()
    parser.feed(inner)
    parser.close()
    return parser.html()


def _looks_like_spacer(raw: str, fragment: str) -> bool:
    compact = re.sub(r"\s+", "", html.unescape(fragment)).replace("\xa0", "")
    zero_font = re.search(
        r"font-size\s*:\s*0(?:\s*(?:;|\"|'|>|$)|px|em|rem)",
        raw,
        flags=re.IGNORECASE,
    )
    return not compact or bool(zero_font)


def _html_block_style(raw: str) -> str:
    lower = raw.lower()
    if "font-size:0.72em" in lower or "color:#888" in lower or "color: #888" in lower:
        return _NOTE_STYLE
    return _P_STYLE


def _render_html_block(raw: str) -> str:
    fragment = _html_fragment_to_inline(raw)
    if _looks_like_spacer(raw, fragment):
        return f'<p style="{_SPACER_STYLE}"><br/></p>'
    return f'<p style="{_html_block_style(raw)}">{fragment.strip()}</p>'


def _heading_style(level: int) -> str:
    return _H2_STYLE if level <= 2 else _H3_STYLE


def render_wechat_html(markdown_text: str) -> str:
    """将 Markdown/混合 HTML 转为微信草稿接口更稳的 HTML。"""
    lines = (markdown_text or "").splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            out.append(f'<p style="{_heading_style(level)}">{_inline_markdown(heading.group(2))}</p>')
            i += 1
            continue

        if _HTML_START_RE.match(line):
            block: list[str] = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i].rstrip())
                i += 1
            out.append(_render_html_block("\n".join(block)))
            continue

        if _LIST_ITEM_RE.match(stripped):
            items: list[str] = []
            while i < len(lines):
                item = _LIST_ITEM_RE.match(lines[i].strip())
                if not item:
                    break
                items.append(f'<li style="{_LI_STYLE}">{_inline_markdown(item.group(1))}</li>')
                i += 1
            out.append(f'<ul style="margin: 0 0 1em; padding-left: 1.2em;">{"".join(items)}</ul>')
            continue

        if _ORDERED_LIST_RE.match(stripped):
            items = []
            while i < len(lines):
                item = _ORDERED_LIST_RE.match(lines[i].strip())
                if not item:
                    break
                items.append(f'<li style="{_LI_STYLE}">{_inline_markdown(item.group(1))}</li>')
                i += 1
            out.append(f'<ol style="margin: 0 0 1em; padding-left: 1.2em;">{"".join(items)}</ol>')
            continue

        if _BLOCKQUOTE_RE.match(stripped):
            quotes: list[str] = []
            while i < len(lines):
                q = _BLOCKQUOTE_RE.match(lines[i].strip())
                if not q:
                    break
                if q.group(1).strip():
                    quotes.append(q.group(1).strip())
                i += 1
            inner = "<br/>".join(_inline_markdown(q) for q in quotes)
            out.append(f'<p style="{_QUOTE_STYLE}">{inner}</p>')
            continue

        if _FENCE_RE.match(stripped):
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not _FENCE_RE.match(lines[i].strip()):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines) and _FENCE_RE.match(lines[i].strip()):
                i += 1
            code_text = html.escape("\n".join(code_lines))
            out.append(f'<p style="{_CODE_STYLE}">{code_text}</p>')
            continue

        paragraph: list[str] = []
        while i < len(lines):
            current = lines[i]
            current_stripped = current.strip()
            if not current_stripped:
                break
            if paragraph and (
                _HEADING_RE.match(current_stripped)
                or _HTML_START_RE.match(current)
                or _LIST_ITEM_RE.match(current_stripped)
                or _ORDERED_LIST_RE.match(current_stripped)
                or _BLOCKQUOTE_RE.match(current_stripped)
                or _FENCE_RE.match(current_stripped)
            ):
                break
            paragraph.append(current.rstrip())
            i += 1
        if paragraph:
            inner = "<br/>".join(_inline_markdown(ln) for ln in paragraph)
            out.append(f'<p style="{_P_STYLE}">{inner}</p>')
        else:
            i += 1
    return "\n".join(out)


def render_wechat_html_safe(markdown_text: str) -> tuple[str, str | None]:
    try:
        return render_wechat_html(markdown_text), None
    except Exception as exc:  # noqa: BLE001 - 预览/发布前转换必须兜底
        safe = html.escape((markdown_text or "").strip())
        return (f'<p style="{_P_STYLE}">{safe}</p>' if safe else ""), str(exc)
