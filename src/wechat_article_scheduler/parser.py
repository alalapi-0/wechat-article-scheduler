"""解析 inbox 中的 Markdown / 文本 / HTML 文章。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
SUMMARY_RE = re.compile(r"^summary:\s*(.+)$", re.MULTILINE | re.IGNORECASE)


@dataclass
class ParsedArticle:
    """解析结果，供入库与去重使用。"""

    source_path: str
    title: str
    summary: str
    body: str
    content_hash: str


def _normalize_title(title: str) -> str:
    return " ".join(title.strip().lower().split())


def content_hash(title: str, body: str) -> str:
    """根据标题+正文生成稳定哈希。"""
    payload = f"{_normalize_title(title)}\n{body.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    block = match.group(1)
    rest = text[match.end() :]
    meta: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip()
    return meta, rest


def _title_from_html(text: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, flags=re.IGNORECASE | re.DOTALL)
    if h1:
        inner = re.sub(r"<[^>]+>", "", h1.group(1))
        return re.sub(r"\s+", " ", inner).strip()
    return None


def _first_heading_md(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def make_summary(body: str, max_chars: int = 200) -> str:
    """从正文生成简短摘要。"""
    plain = re.sub(r"<[^>]+>", "", body)
    plain = re.sub(r"[#*_>`]", "", plain)
    plain = " ".join(plain.split())
    if len(plain) <= max_chars:
        return plain
    return plain[: max_chars - 1].rstrip() + "…"


def parse_file(path: Path, *, summary_max_chars: int = 200) -> ParsedArticle:
    """读取并解析单个文件。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix in {".md", ".txt"}:
        meta, body = _extract_frontmatter(raw)
        title = meta.get("title") or _first_heading_md(body) or path.stem
        summary = meta.get("summary") or make_summary(body, summary_max_chars)
    elif suffix == ".html":
        body = raw
        title = _title_from_html(raw) or path.stem
        summary = make_summary(body, summary_max_chars)
    else:
        body = raw
        title = path.stem
        summary = make_summary(body, summary_max_chars)

    title = title.strip() or path.stem
    ch = content_hash(title, body)
    return ParsedArticle(
        source_path=str(path),
        title=title,
        summary=summary,
        body=body,
        content_hash=ch,
    )
