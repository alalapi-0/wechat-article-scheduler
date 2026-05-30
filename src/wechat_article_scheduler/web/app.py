"""FastAPI 管理后台（Round 6）：文章列表、队列、事件与手动触发。"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig, load_config
from wechat_article_scheduler.events_cli import list_events
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.scheduler import run_due_jobs


def create_app(config: AppConfig | None = None) -> FastAPI:
    """创建 FastAPI 应用（可注入 config 便于测试）。"""
    cfg = config or load_config()
    app = FastAPI(title="微信公众号文章调度器", description="本地管理后台（默认 mock）")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        """简易中文管理页（无需前端构建）。"""
        return _ADMIN_HTML

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return {
            "wechat_mode": cfg.wechat_mode,
            "dry_run": cfg.dry_run,
            "database": str(cfg.database_path),
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
        return scan_inbox(cfg)

    @app.post("/api/plan")
    def trigger_plan() -> dict[str, Any]:
        return build_plan(cfg)

    @app.post("/api/run-once")
    def trigger_run_once() -> dict[str, Any]:
        return run_due_jobs(cfg)

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


_ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>文章调度器管理后台</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 24px; max-width: 960px; }
    h1 { font-size: 1.4rem; }
    button { margin: 4px 8px 4px 0; padding: 6px 12px; cursor: pointer; }
    pre { background: #f4f4f4; padding: 12px; overflow: auto; font-size: 13px; }
    .hint { color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <h1>微信公众号文章调度器</h1>
  <p class="hint">默认 mock 模式，不会调用真实微信 API。点击下方按钮触发 CLI 同等操作。</p>
  <div>
    <button onclick="post('/api/scan')">扫描 inbox</button>
    <button onclick="post('/api/plan')">生成计划</button>
    <button onclick="post('/api/run-once')">执行到期任务</button>
    <button onclick="load('/api/status')">刷新状态</button>
  </div>
  <h2>状态</h2>
  <pre id="out">加载中…</pre>
  <script>
    async function load(url) {
      const r = await fetch(url);
      document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
    }
    async function post(url) {
      const r = await fetch(url, { method: 'POST' });
      document.getElementById('out').textContent = JSON.stringify(await r.json(), null, 2);
    }
    load('/api/status');
    load('/api/articles').then(d => {
      const el = document.getElementById('out');
      el.textContent = '文章列表:\\n' + JSON.stringify(d, null, 2);
    });
  </script>
</body>
</html>
"""
