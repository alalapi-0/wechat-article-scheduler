"""单篇作品草稿创建前检查摘要（作品卡片与详情页共用）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.cover_assets.index import check_configured_cover
from wechat_article_scheduler.publish_body import publish_body_for
from wechat_article_scheduler.publish_preview import _maybe_unescape_html
from wechat_article_scheduler.web.user_copy import label_mode


def article_preflight_checks(row: dict[str, Any], config: AppConfig) -> list[dict[str, Any]]:
    """与作品详情页一致的检查项列表。"""
    checks: list[dict[str, Any]] = []
    mode = (config.wechat_mode or "mock").strip().lower()

    checks.append(
        {
            "id": "mode",
            "ok": True,
            "label": "运行模式",
            "detail": label_mode(mode),
        }
    )

    cover = check_configured_cover(config, row.get("cover_path"))
    checks.append(
        {
            "id": "cover",
            "ok": bool(cover["ok"]),
            "label": "封面",
            "detail": str(cover["message"]),
        }
    )

    summary = (row.get("summary") or "").strip()
    digest_truncated = bool(summary) and len(summary) > 120
    checks.append(
        {
            "id": "digest",
            "ok": not digest_truncated,
            "label": "摘要",
            "detail": "摘要长度正常"
            if not digest_truncated
            else "摘要超过 120 字，创建草稿时将截断",
        }
    )

    title = (row.get("title") or "").strip()
    body = row.get("body") or ""
    if not body.strip():
        checks.append({"id": "body", "ok": False, "label": "正文", "detail": "正文为空"})
    elif title and publish_body_for(title, body) != body.strip():
        checks.append(
            {
                "id": "title_dup",
                "ok": False,
                "label": "标题重复",
                "detail": "正文首行与标题重复，创建草稿时会自动处理",
            }
        )
    if "&lt;" in body and _maybe_unescape_html(body) != body:
        checks.append(
            {
                "id": "html",
                "ok": False,
                "label": "正文格式",
                "detail": "正文疑似转义 HTML，请先预览确认",
            }
        )

    for c in checks:
        if c["id"] == "body" and not c.get("ok"):
            c["required"] = True
        elif c["id"] in ("cover", "html") and mode == "real" and not c.get("ok"):
            c["required"] = True
        else:
            c["required"] = False
    return checks


def build_article_preflight_summary(row: dict[str, Any], config: AppConfig) -> dict[str, Any]:
    checks = article_preflight_checks(row, config)
    issues = [c for c in checks if not c.get("ok") and c["id"] != "mode"]
    blocking = [c for c in checks if c.get("required")]
    ready = len(blocking) == 0
    if blocking:
        bar_level = "err"
        bar_text = blocking[0].get("detail") or "草稿创建前检查未通过"
    elif issues:
        bar_level = "warn"
        bar_text = issues[0].get("detail") or "有预检提示"
    else:
        bar_level = "ok"
        bar_text = "草稿创建前检查通过"
    return {
        "ready": ready,
        "blocking_count": len(blocking),
        "issue_count": len(issues),
        "bar_level": bar_level,
        "bar_text": bar_text,
        "checks": checks,
    }
