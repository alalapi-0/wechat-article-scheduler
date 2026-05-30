"""FastAPI 管理后台（Round 6）：文章列表、队列、事件与手动触发。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig, load_config
from wechat_article_scheduler.events_cli import list_events
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.content_library import list_collections, list_content_items
from wechat_article_scheduler.cover_assets import check_cover_path, index_cover_directory
from wechat_article_scheduler.renderers import render_markdown_to_html_safe
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.web.user_copy import (
    export_labels_json,
    humanize_plan_result,
    humanize_run_once_result,
    humanize_scan_result,
)

_TEMPLATE_PATH = Path(__file__).parent / "admin_template.html"
_ADMIN_HTML = _TEMPLATE_PATH.read_text(encoding="utf-8") if _TEMPLATE_PATH.exists() else "<html><body>模板缺失</body></html>"


def create_app(config: AppConfig | None = None) -> FastAPI:
    """创建 FastAPI 应用（可注入 config 便于测试）。"""
    cfg = config or load_config()
    app = FastAPI(title="微信公众号文章调度器", description="本地管理后台（默认 mock）")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        """普通用户工作台首页（Desktop-first）。"""
        return _ADMIN_HTML

    @app.get("/debug", response_class=HTMLResponse)
    def debug_page() -> str:
        """高级排错页：展示原始 JSON 与内部字段。"""
        return _DEBUG_HTML

    @app.get("/api/user-labels")
    def user_labels() -> dict[str, Any]:
        return export_labels_json()

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return {
            "wechat_mode": cfg.wechat_mode,
            "dry_run": cfg.dry_run,
            "wechat_enable_publish": cfg.wechat_enable_publish,
            "database": str(cfg.database_path),
        }

    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        """工作台首页聚合数据：状态摘要、最近任务与事件。"""
        with db.connect(cfg.database_path) as conn:
            article_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM articles GROUP BY status"
            ).fetchall()
            job_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM publish_jobs GROUP BY status"
            ).fetchall()
            recent_jobs = conn.execute(
                """
                SELECT j.id, j.article_id, j.scheduled_at, j.status, j.retry_count,
                       j.adapter_mode, j.updated_at, a.title
                FROM publish_jobs j
                JOIN articles a ON a.id = j.article_id
                ORDER BY j.updated_at DESC, j.id DESC
                LIMIT 10
                """
            ).fetchall()
        return {
            "status": status(),
            "article_counts": {str(r["status"]): int(r["count"]) for r in article_rows},
            "job_counts": {str(r["status"]): int(r["count"]) for r in job_rows},
            "recent_jobs": [dict(r) for r in recent_jobs],
            "recent_events": [dict(r) for r in list_events(cfg, limit=10)],
            "docs": [
                {"label": "README", "path": "README.md"},
                {"label": "开发路线图", "path": "docs/rounds.md"},
                {"label": "Web 控制台设计", "path": "docs/web_console_design.md"},
            ],
        }

    @app.get("/api/articles")
    def articles(limit: int = 50) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            rows = conn.execute(
                """
                SELECT id, title, status, source_path, created_at, updated_at
                FROM articles ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    @app.get("/api/jobs")
    def jobs(limit: int = 50) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            rows = conn.execute(
                """
                SELECT j.id, j.article_id, j.scheduled_at, j.status, j.retry_count,
                       a.title
                FROM publish_jobs j
                JOIN articles a ON a.id = j.article_id
                ORDER BY j.scheduled_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    @app.get("/api/events")
    def events(limit: int = 30) -> list[dict[str, Any]]:
        rows = list_events(cfg, limit=limit)
        return [dict(r) for r in rows]

    @app.post("/api/scan")
    def trigger_scan() -> dict[str, Any]:
        result = scan_inbox(cfg)
        result["human"] = humanize_scan_result(result)
        return result

    @app.post("/api/plan")
    def trigger_plan() -> dict[str, Any]:
        result = build_plan(cfg)
        result["human"] = humanize_plan_result(result)
        return result

    @app.post("/api/run-once")
    def trigger_run_once() -> dict[str, Any]:
        result = run_due_jobs(cfg)
        result["human"] = humanize_run_once_result(result)
        return result

    @app.get("/api/cover-assets")
    def cover_assets_index() -> dict[str, Any]:
        root = cfg.root / "cover_assets"
        assets = index_cover_directory(root)
        check = check_cover_path(
            None,
            default_thumb=Path(cfg.wechat_default_thumb_path)
            if cfg.wechat_default_thumb_path
            else None,
        )
        return {
            "directory": str(root),
            "assets": [
                {"path": a.path, "name": a.name, "size_bytes": a.size_bytes}
                for a in assets
            ],
            "publish_check": check,
        }

    @app.get("/api/content-library")
    def content_library_view(
        collection: str | None = None,
        review_status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            items = list_content_items(
                conn,
                limit=limit,
                collection_slug=collection,
                review_status=review_status,  # type: ignore[arg-type]
            )
            collections = list_collections(conn)
        return {
            "collections": [c.__dict__ for c in collections],
            "items": [
                {
                    "article_id": i.article_id,
                    "title": i.title,
                    "review_status": i.review_status,
                    "collection_slug": i.collection_slug,
                    "tags": list(i.tags),
                }
                for i in items
            ],
        }

    @app.get("/api/articles/{article_id}/render-preview")
    def article_render_preview(article_id: int) -> dict[str, Any]:
        """只读 HTML 预览（不调用微信 API）。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                "SELECT id, title, summary, body FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        html_body, render_error = render_markdown_to_html_safe(row["body"] or "")
        return {
            "article_id": article_id,
            "title": (row["title"] or "").strip() or f"文章 {article_id}",
            "summary": (row["summary"] or "").strip(),
            "html_body": html_body,
            "render_error": render_error,
            "read_only": True,
        }

    @app.get("/api/drafts/preview/{article_id}")
    def draft_preview(article_id: int) -> JSONResponse:
        """Mock/Real 适配器草稿预览（不写入微信）。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                "SELECT id, title, summary, body FROM articles WHERE id = ?",
                (article_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        adapter = get_adapter(cfg)
        preview = {
            "article_id": article_id,
            "title": row["title"],
            "summary": row["summary"],
            "body_preview": (row["body"] or "")[:500],
            "mode": cfg.wechat_mode,
            "note": "预览模式：mock 会生成本地 media_id；real 模式需显式调用 create_draft 才会联网",
        }
        if cfg.wechat_mode == "mock":
            draft = adapter.create_draft(
                title=row["title"],
                summary=row["summary"] or "",
                body=row["body"],
            )
            preview["mock_media_id"] = draft.media_id
            preview["raw"] = draft.raw_response
        return JSONResponse(preview)

    return app


_DEBUG_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>高级排错</title>
<style>body{font-family:system-ui,sans-serif;padding:20px;max-width:960px;margin:0 auto}
pre{background:#111;color:#eee;padding:12px;border-radius:8px;overflow:auto}</style></head>
<body>
<h1>高级排错（开发者/Agent）</h1>
<p>此处展示内部字段与原始 JSON，普通用户无需查看。<a href="/">返回工作台</a></p>
<h2>状态</h2><pre id="status">加载中…</pre>
<h2>概况</h2><pre id="overview">加载中…</pre>
<script>
Promise.all([fetch('/api/status'), fetch('/api/overview')]).then(async ([a,b])=>{
  document.getElementById('status').textContent = JSON.stringify(await a.json(), null, 2);
  document.getElementById('overview').textContent = JSON.stringify(await b.json(), null, 2);
});
</script></body></html>"""
