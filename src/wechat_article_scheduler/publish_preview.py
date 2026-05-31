"""统一发布预览与草稿正文 HTML 构建（Web 预览与 real draft 同源）。"""

from __future__ import annotations

import html as html_module
from typing import Any

from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.renderers import render_wechat_html, render_wechat_html_safe


def _maybe_unescape_html(body: str) -> str:
    """将误存为实体转义的 HTML 还原为可渲染源码。"""
    stripped = (body or "").lstrip()
    if not stripped or stripped.startswith("<"):
        return body or ""
    if "&lt;" not in stripped and "&gt;" not in stripped and "&amp;" not in stripped:
        return body or ""
    unescaped = html_module.unescape(body)
    if unescaped.lstrip().startswith("<"):
        return unescaped
    return body or ""


def normalized_body_for_publish(title: str, body: str) -> str:
    """发布前正文：实体归一化 + 去掉与 title 重复的首标题。"""
    return publish_body_for(title, _maybe_unescape_html(body))


def render_for_publish(title: str, body: str) -> str:
    """与微信 draft/add content 字段一致的公众号兼容 HTML。"""
    return render_wechat_html(normalized_body_for_publish(title, body))


def build_publish_preview(
    title: str,
    summary: str,
    body: str,
    *,
    article_id: int | None = None,
) -> dict[str, Any]:
    """构建 Web/API 预览载荷；raw_body 供高级信息区展示原始内容。"""
    raw = body or ""
    prepared = normalized_body_for_publish(title or "", raw)
    html_body, render_error = render_wechat_html_safe(prepared)
    out: dict[str, Any] = {
        "title": (title or "").strip() or (f"文章 {article_id}" if article_id else "未命名"),
        "summary": (summary or "").strip(),
        "html_body": html_body,
        "raw_body": raw,
        "render_error": render_error,
        "read_only": True,
    }
    if article_id is not None:
        out["article_id"] = article_id
    return out
