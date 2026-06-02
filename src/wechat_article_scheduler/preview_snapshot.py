"""公众号效果预览快照（收敛 Phase 1 Round 5 / Round 60）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.content_quality import article_content_hints
from wechat_article_scheduler.parser import clamp_summary
from wechat_article_scheduler.publish_preview import build_publish_preview

APPROXIMATION_NOTE = (
    "以下为本地渲染的近似公众号正文预览，不等同于微信后台编辑器；"
    "标题单独显示在公众号标题栏。"
)
SNAPSHOT_VERSION = 1


def preview_snapshots_dir(config: AppConfig) -> Path:
    return config.root / "storage" / "preview_snapshots"


def build_article_preview_package(
    config: AppConfig,
    row: Any,
    *,
    article_id: int,
) -> dict[str, Any]:
    """统一预览入口：摘要、正文 HTML、封面、质量提示与近似说明。"""
    title = row["title"] or ""
    summary = row["summary"] or ""
    body = row["body"] or ""
    base = build_publish_preview(title, summary, body, article_id=article_id)
    digest = clamp_summary((summary or "").strip() or title, 120)
    digest_truncated = bool(summary.strip()) and len(summary.strip()) > 120
    cover_path = (row["cover_path"] if "cover_path" in row.keys() else None) or ""
    cover_path = str(cover_path).strip()
    has_cover = bool(cover_path)
    hints = article_content_hints(title, body)
    pkg: dict[str, Any] = {
        **base,
        "snapshot_version": SNAPSHOT_VERSION,
        "approximation_note": APPROXIMATION_NOTE,
        "digest_preview": digest,
        "digest_truncated": digest_truncated,
        "cover_path": cover_path,
        "has_cover": has_cover,
        "cover_url": f"/media/cover/{article_id}" if has_cover else None,
        "content_hints": hints,
        "blocking_hints": [h for h in hints if h in ("正文为空", "疑似 HTML 源码")],
    }
    return pkg


def save_preview_snapshot(config: AppConfig, package: dict[str, Any]) -> Path:
    """将预览包写入 storage/preview_snapshots/（JSON + 可选 HTML）。"""
    article_id = int(package.get("article_id") or 0)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = preview_snapshots_dir(config)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"article_{article_id}_{stamp}"
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_version": package.get("snapshot_version", SNAPSHOT_VERSION),
        "package": package,
    }
    json_path = base.with_suffix(".json")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path = base.with_suffix(".html")
    html_path.write_text(_snapshot_html_document(package), encoding="utf-8")
    return json_path


def _snapshot_html_document(package: dict[str, Any]) -> str:
    title = package.get("title") or "未命名"
    summary = package.get("summary") or ""
    body_html = package.get("html_body") or ""
    note = package.get("approximation_note") or APPROXIMATION_NOTE
    hints = package.get("content_hints") or []
    hint_block = ""
    if hints:
        hint_block = "<ul>" + "".join(f"<li>{h}</li>" for h in hints) + "</ul>"
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>预览快照 — {title}</title></head><body>"
        f"<p><em>{note}</em></p>"
        f"<h1>{title}</h1>"
        f"<p style=\"color:#888\">摘要：{summary}</p>"
        f"{hint_block}"
        f"<div>{body_html}</div></body></html>"
    )


def latest_snapshot_path(config: AppConfig, article_id: int) -> Path | None:
    out_dir = preview_snapshots_dir(config)
    if not out_dir.is_dir():
        return None
    matches = sorted(out_dir.glob(f"article_{article_id}_*.json"), reverse=True)
    return matches[0] if matches else None
