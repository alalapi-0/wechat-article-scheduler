"""发布前内容质量检查（Round 53，供调度器与 Web 预检共用）。"""

from __future__ import annotations

from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_preview import _maybe_unescape_html


def content_block_reason(title: str, body: str) -> str | None:
    """真实正式发布路径上的严重内容问题（mock/仅草稿不阻断）。"""
    raw = body or ""
    if not raw.strip():
        return "正文为空"
    if "&lt;" in raw and _maybe_unescape_html(raw) != raw:
        return "疑似 HTML 源码"
    return None


def article_content_hints(title: str, body: str) -> list[str]:
    """作品卡片轻量质量提示。"""
    hints: list[str] = []
    raw = body or ""
    if not raw.strip():
        hints.append("正文为空")
    if (title or "").strip() and publish_body_for(title or "", raw) != raw.strip():
        hints.append("标题或重复首行")
    if "&lt;" in raw and _maybe_unescape_html(raw) != raw:
        hints.append("疑似 HTML 源码")
    return hints
