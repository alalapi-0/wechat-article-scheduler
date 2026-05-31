"""发布正文规范化：标题仅出现在微信 title 字段，正文去掉重复首标题。"""

from __future__ import annotations

import re

from wechat_article_scheduler.parser import _normalize_title

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_HTML_H1_RE = re.compile(
    r"^\s*<h1\b[^>]*>(.*?)</h1>\s*",
    re.IGNORECASE | re.DOTALL,
)


def _titles_match(left: str, right: str) -> bool:
    return _normalize_title(left) == _normalize_title(right)


def _strip_html_duplicate_h1(title: str, body: str) -> str:
    match = _HTML_H1_RE.match(body)
    if not match:
        return body
    inner = re.sub(r"<[^>]+>", "", match.group(1))
    inner = re.sub(r"\s+", " ", inner).strip()
    if not _titles_match(title, inner):
        return body
    return body[match.end() :].lstrip("\n\r\t ")


def _strip_markdown_duplicate_heading(title: str, body: str) -> str:
    lines = body.splitlines()
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines):
        return body
    m = _MD_HEADING_RE.match(lines[idx].strip())
    if not m or not _titles_match(title, m.group(2)):
        return body
    idx += 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    return "\n".join(lines[idx:]).lstrip("\n")


def publish_body_for(title: str, body: str) -> str:
    """
    返回用于发布/草稿的正文：若首段标题与文章 title 重复则移除。

    不修改数据库中的原始 body；仅在 adapter 渲染前调用。
    """
    raw = body or ""
    if not raw.strip() or not (title or "").strip():
        return raw
    stripped = raw.lstrip()
    if stripped.startswith("<"):
        return _strip_html_duplicate_h1(title, raw)
    return _strip_markdown_duplicate_heading(title, raw)
