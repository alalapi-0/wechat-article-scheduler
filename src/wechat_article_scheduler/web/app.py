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
        return scan_inbox(cfg)

    @app.post("/api/plan")
    def trigger_plan() -> dict[str, Any]:
        return build_plan(cfg)

    @app.post("/api/run-once")
    def trigger_run_once() -> dict[str, Any]:
        return run_due_jobs(cfg)

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


_ADMIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>文章调度器基础工作台</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --primary: #2563eb;
      --primary-soft: #dbeafe;
      --ok: #166534;
      --ok-soft: #dcfce7;
      --warn: #9a3412;
      --warn-soft: #ffedd5;
      --err: #991b1b;
      --err-soft: #fee2e2;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
    }
    .wrap {
      max-width: 1040px;
      margin: 0 auto;
      padding: 22px 20px 40px;
    }
    .header {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 18px 20px;
      margin-bottom: 14px;
    }
    .title {
      margin: 0 0 6px;
      font-size: 1.45rem;
      line-height: 1.35;
    }
    .subtle {
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .grid {
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px 16px;
    }
    .panel h2 {
      margin: 0 0 10px;
      font-size: 1.05rem;
    }
    .helper {
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .mode-badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 2px 9px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #f3f4f6;
      margin-left: 8px;
      vertical-align: middle;
    }
    .mode-badge.mock {
      color: #1d4ed8;
      background: #dbeafe;
      border-color: #bfdbfe;
    }
    .mode-badge.real {
      color: var(--warn);
      background: var(--warn-soft);
      border-color: #fdba74;
    }
    .cards {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fafafa;
    }
    .card strong {
      display: block;
      font-size: 1.35rem;
      line-height: 1.2;
      overflow-wrap: anywhere;
      word-break: break-word;
    }
    .card span {
      color: var(--muted);
      font-size: 13px;
    }
    .btn-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    button {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 14px;
      cursor: pointer;
    }
    button.primary {
      background: var(--primary);
      border-color: #1d4ed8;
      color: #fff;
    }
    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
    .status-inline {
      color: var(--muted);
      font-size: 13px;
      min-height: 18px;
    }
    .alert {
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 10px;
      border: 1px solid var(--line);
      font-size: 14px;
      line-height: 1.45;
    }
    .alert.info {
      color: #1e3a8a;
      background: var(--primary-soft);
      border-color: #bfdbfe;
    }
    .alert.ok {
      color: var(--ok);
      background: var(--ok-soft);
      border-color: #86efac;
    }
    .alert.error {
      color: var(--err);
      background: var(--err-soft);
      border-color: #fca5a5;
    }
    .result-box {
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fafafa;
      font-size: 14px;
    }
    .result-title {
      margin: 0 0 8px;
      font-weight: 600;
    }
    .result-list {
      margin: 0;
      padding-left: 18px;
      color: #374151;
    }
    .result-list li {
      margin-bottom: 4px;
    }
    #jobsArea, #eventsArea {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 8px 6px;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 600;
      background: #fafafa;
    }
    .empty {
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 12px;
      background: #fafafa;
      font-size: 14px;
      line-height: 1.45;
    }
    .doc-links {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .doc-links a {
      color: var(--primary);
      background: var(--primary-soft);
      border: 1px solid #bfdbfe;
      border-radius: 999px;
      padding: 5px 10px;
      text-decoration: none;
      font-size: 13px;
    }
    .pill {
      display: inline-flex;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      background: #f3f4f6;
      border: 1px solid var(--line);
    }
    pre {
      background: #111827;
      color: #f9fafb;
      border-radius: 8px;
      padding: 10px;
      overflow: auto;
      font-size: 12px;
      margin: 10px 0 0;
      max-height: 280px;
    }
    details {
      margin-top: 10px;
    }
    .risk-tip {
      margin-top: 8px;
      font-size: 13px;
      color: var(--warn);
      background: var(--warn-soft);
      border: 1px solid #fdba74;
      border-radius: 8px;
      padding: 8px 10px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="header">
      <h1 class="title">微信公众号文章调度器基础工作台 <span id="modeBadge" class="mode-badge">mode: --</span></h1>
      <p class="subtle">本地微信公众号文章发布工作台。默认 mock 模式，不会调用真实微信 API；real 模式仍以草稿和人工确认为边界。</p>
    </header>

    <div id="alert" class="alert info">正在初始化页面…</div>

    <div class="grid">
      <section class="panel">
        <h2>安全状态</h2>
        <p class="helper">确认当前运行模式、发布开关和数据库位置。真实发布默认不应无人值守启用。</p>
        <div id="safetyCards" class="cards">
          <div class="card"><strong>--</strong><span>加载中</span></div>
        </div>
        <div id="riskTip" class="risk-tip" style="display:none;">
          当前为 real 模式：请确认 WECHAT_ENABLE_PUBLISH 与人工审核流程，避免误发布。
        </div>
      </section>

      <section class="panel">
        <h2>操作区</h2>
        <p class="helper">建议顺序：扫描 inbox → 生成发布计划 → 执行到期任务。刷新状态只读，不会写库。</p>
        <div class="btn-row">
          <button class="primary js-action" data-url="/api/scan" data-method="POST" data-action="scan">扫描 inbox</button>
          <button class="primary js-action" data-url="/api/plan" data-method="POST" data-action="plan">生成计划</button>
          <button class="primary js-action" data-url="/api/run-once" data-method="POST" data-action="run-once">执行到期任务</button>
        </div>
        <div class="btn-row">
          <button class="js-action" data-url="/api/status" data-method="GET" data-action="status">刷新状态</button>
        </div>
        <div id="opStatus" class="status-inline">空闲</div>
      </section>
    </div>

    <section class="panel" style="margin-top: 14px;">
      <h2>结果区</h2>
      <p class="helper">展示最近一次操作结果；失败时会附带下一步建议。</p>
      <div id="resultBox" class="result-box">
        <p class="result-title">等待操作</p>
        <ul class="result-list">
          <li>点击上方按钮开始</li>
        </ul>
      </div>
    </section>

    <section class="panel" style="margin-top: 14px;">
      <h2>状态卡片</h2>
      <p class="helper">把 scan / plan / run-once 的关键统计转成可读卡片，原始 JSON 仍可在结果区展开。</p>
      <div id="metricCards" class="cards">
        <div class="card"><strong>--</strong><span>等待加载</span></div>
      </div>
    </section>

    <div class="grid" style="margin-top: 14px;">
      <section class="panel">
        <h2>发布队列 / 最近任务</h2>
        <p class="helper">来自 publish_jobs。后续 Round 会补更完整的筛选、重试和人工审核闸门。</p>
        <div id="jobsArea" class="empty">正在加载任务队列…</div>
      </section>

      <section class="panel">
        <h2>事件日志</h2>
        <p class="helper">来自 events，用于追踪扫描、排期、执行、失败和 warning。</p>
        <div id="eventsArea" class="empty">正在加载事件日志…</div>
      </section>
    </div>

    <section class="panel" style="margin-top: 14px;">
      <h2>文档入口</h2>
      <p class="helper">路线图以 docs/rounds.md 为人类权威；Web 设计继续保持轻量、无重前端框架。</p>
      <div id="docsArea" class="doc-links">
        <a href="/docs/rounds.md">docs/rounds.md</a>
      </div>
    </section>
  </div>

  <script>
    const buttons = Array.from(document.querySelectorAll('.js-action'));
    const alertEl = document.getElementById('alert');
    const opStatusEl = document.getElementById('opStatus');
    const safetyCardsEl = document.getElementById('safetyCards');
    const metricCardsEl = document.getElementById('metricCards');
    const jobsAreaEl = document.getElementById('jobsArea');
    const eventsAreaEl = document.getElementById('eventsArea');
    const docsAreaEl = document.getElementById('docsArea');
    const resultBoxEl = document.getElementById('resultBox');
    const modeBadgeEl = document.getElementById('modeBadge');
    const riskTipEl = document.getElementById('riskTip');

    let busy = false;
    let lastActionAt = null;

    function fmtTime(dateObj) {
      return dateObj ? dateObj.toLocaleString('zh-CN', { hour12: false }) : '未执行';
    }

    function setAlert(type, message) {
      alertEl.className = 'alert ' + type;
      alertEl.textContent = message;
    }

    function setBusy(nextBusy, text) {
      busy = nextBusy;
      buttons.forEach((btn) => { btn.disabled = nextBusy; });
      opStatusEl.textContent = text || (nextBusy ? '处理中…' : '空闲');
    }

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function card(value, label) {
      return `<div class="card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
    }

    function renderSafety(data) {
      const status = data.status || data;
      const mode = String(status.wechat_mode || '').toLowerCase();
      const publishState = status.wechat_enable_publish ? 'publish enabled' : 'publish disabled';
      const draftState = mode === 'real' && !status.wechat_enable_publish ? 'real draft only' : mode;
      safetyCardsEl.innerHTML = [
        card(status.wechat_mode || '--', '运行模式'),
        card(status.dry_run ? 'on' : 'off', 'DRY_RUN'),
        card(publishState, '真实发布开关'),
        card(draftState || '--', '安全提示'),
        card(fmtTime(lastActionAt), '最近操作'),
        card(status.database || '--', 'SQLite 数据库'),
      ].join('');
      modeBadgeEl.textContent = 'mode: ' + (mode || '--');
      modeBadgeEl.classList.toggle('mock', mode === 'mock');
      modeBadgeEl.classList.toggle('real', mode === 'real');
      riskTipEl.style.display = mode === 'real' ? 'block' : 'none';
    }

    function renderMetricCards(data) {
      const articleCounts = data.article_counts || {};
      const jobCounts = data.job_counts || {};
      metricCardsEl.innerHTML = [
        card(articleCounts.imported || 0, '文章 imported'),
        card(articleCounts.published || 0, '文章 published'),
        card(jobCounts.pending || 0, '任务 pending'),
        card(jobCounts.done || 0, '任务 done'),
        card(jobCounts.failed || 0, '任务 failed'),
        card(jobCounts.running || 0, '任务 running'),
      ].join('');
    }

    function renderJobs(rows) {
      if (!rows || rows.length === 0) {
        jobsAreaEl.className = 'empty';
        jobsAreaEl.textContent = '暂无 publish_jobs。请先扫描 inbox 并生成计划；更完整的队列筛选会在后续 Round 实现。';
        return;
      }
      jobsAreaEl.className = '';
      jobsAreaEl.innerHTML = `
        <table>
          <thead><tr><th>ID</th><th>标题</th><th>计划时间</th><th>状态</th><th>重试</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.id)}</td>
                <td>${escapeHtml(row.title || '(无标题)')}</td>
                <td>${escapeHtml(row.scheduled_at || '--')}</td>
                <td><span class="pill">${escapeHtml(row.status || '--')}</span></td>
                <td>${escapeHtml(row.retry_count ?? 0)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function renderEvents(rows) {
      if (!rows || rows.length === 0) {
        eventsAreaEl.className = 'empty';
        eventsAreaEl.textContent = '暂无 events。执行 scan / plan / run-once 后会在这里出现审计事件。';
        return;
      }
      eventsAreaEl.className = '';
      eventsAreaEl.innerHTML = `
        <table>
          <thead><tr><th>时间</th><th>类型</th><th>对象</th><th>摘要</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.created_at || '--')}</td>
                <td><span class="pill">${escapeHtml(row.event_type || '--')}</span></td>
                <td>${escapeHtml(row.entity_type || '--')} #${escapeHtml(row.entity_id ?? '-')}</td>
                <td>${escapeHtml(row.payload_json || '')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    function renderDocs(rows) {
      docsAreaEl.innerHTML = (rows || [])
        .map((row) => `<a href="/${escapeHtml(row.path)}" title="${escapeHtml(row.path)}">${escapeHtml(row.label)}</a>`)
        .join('');
    }

    async function refreshOverview() {
      const response = await fetch('/api/overview');
      if (!response.ok) throw new Error('无法刷新 overview');
      const data = await response.json();
      renderSafety(data);
      renderMetricCards(data);
      renderJobs(data.recent_jobs);
      renderEvents(data.recent_events);
      renderDocs(data.docs);
      return data;
    }

    function nextStepHints(action, success) {
      if (success) {
        if (action === 'scan') return ['建议继续执行 plan 生成任务队列。'];
        if (action === 'plan') return ['建议执行 run-once 触发到期任务。'];
        if (action === 'run-once') return ['可执行 status 或 events 检查执行结果。'];
        return ['状态已更新。'];
      }
      return [
        '可先重试一次当前操作。',
        '确认已执行 init-db 且数据库路径可写。',
        '检查配置：WECHAT_MODE、rules.yaml 与输入目录是否正确。',
      ];
    }

    function renderResult(action, payload, success) {
      const title = success ? `操作成功：${action}` : `操作失败：${action}`;
      const flatEntries = Object.entries(payload || {}).slice(0, 8);
      const points = flatEntries.length
        ? flatEntries.map(([k, v]) => `<li><strong>${k}</strong>: ${String(v)}</li>`).join('')
        : '<li>无返回字段</li>';
      const hints = nextStepHints(action, success).map((item) => `<li>${item}</li>`).join('');
      resultBoxEl.innerHTML = `
        <p class="result-title">${title}</p>
        <ul class="result-list">${points}</ul>
        <p class="result-title" style="margin-top:8px;">下一步建议</p>
        <ul class="result-list">${hints}</ul>
        <details>
          <summary>查看原始 JSON</summary>
          <pre>${JSON.stringify(payload, null, 2)}</pre>
        </details>
      `;
    }

    async function invoke(url, method, action) {
      if (busy) return;
      setBusy(true, `正在执行 ${action}…`);
      setAlert('info', `操作中：${action}，请稍候…`);
      try {
        const response = await fetch(url, { method });
        let data = {};
        try {
          data = await response.json();
        } catch (_e) {
          data = { error: '返回值不是 JSON', status: response.status };
        }
        if (!response.ok) {
          throw new Error((data && (data.detail || data.error)) || `HTTP ${response.status}`);
        }
        lastActionAt = new Date();
        await refreshOverview();
        renderResult(action, data, true);
        setAlert('ok', `完成：${action}`);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        renderResult(action, { error: message }, false);
        setAlert('error', `失败：${action}，${message}`);
      } finally {
        setBusy(false, '空闲');
      }
    }

    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const { url, method, action } = btn.dataset;
        invoke(url, method || 'GET', action || 'unknown');
      });
    });

    refreshOverview()
      .then((data) => {
        renderResult('status', data.status, true);
        setAlert('ok', '页面已加载：当前为本地轻量工作台');
      })
      .catch((err) => {
        renderResult('status', { error: err.message || String(err) }, false);
        setAlert('error', '页面初始化失败，请确认数据库已初始化');
      });
  </script>
</body>
</html>
"""
