"""FastAPI 管理后台（Round 6）：文章列表、队列、事件与手动触发。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig, load_config
from wechat_article_scheduler.events_cli import list_events
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.schedule_assign import (
    assign_article_schedule,
    assign_batch_schedule,
    parse_scheduled_at,
)
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.content_library import (
    discover_collection_configs,
    list_collections,
    list_collections_summary,
    list_content_items,
    sync_discovered_collections,
)
from wechat_article_scheduler.cover_assets import (
    bind_covers_by_stem,
    build_dual_cover_previews,
    check_cover_path,
    index_cover_directory,
    repair_invalid_cover_paths,
    scan_cover_assets,
)
from wechat_article_scheduler.cover_assets.crop_preview import enrich_cover_config
from wechat_article_scheduler.preview_snapshot import (
    build_article_preview_package,
    latest_snapshot_path,
    save_preview_snapshot,
)
from wechat_article_scheduler.scheduler import run_due_jobs
from wechat_article_scheduler.web.user_copy import (
    article_workflow_hint,
    export_labels_json,
    humanize_plan_result,
    humanize_retry_jobs_result,
    humanize_run_once_result,
    humanize_scan_result,
    humanize_schedule_batch_result,
    humanize_schedule_single_result,
)
from wechat_article_scheduler.web.schedule_display import format_scheduled_at, summarize_schedule
from wechat_article_scheduler.web.workbench_mvp import build_workbench_hints
from wechat_article_scheduler.web.article_detail import build_article_detail
from wechat_article_scheduler.web.queue_display import list_queue_jobs, queue_summary
from wechat_article_scheduler.draft_update import humanize_update_result, update_article_wechat_draft
from wechat_article_scheduler.wechat_field_matrix import (
    field_gaps,
    list_field_matrix,
    matrix_summary,
)
from wechat_article_scheduler.adapters.browser_assist import (
    SUPPORTED_BROWSER_ASSIST,
    build_dry_run_plan,
)
from wechat_article_scheduler.adapters.manual_export import (
    SUPPORTED_PLATFORMS,
    export_article_to_outbox,
    list_outbox_packages,
)
from wechat_article_scheduler.review.proof import (
    ProofInput,
    get_proof_for_job,
    list_waiting_confirmation,
    mark_job_waiting_confirmation,
    submit_publish_proof,
)
from wechat_article_scheduler.web.drafts_display import (
    drafts_summary,
    get_wechat_draft,
    list_wechat_drafts,
)
from wechat_article_scheduler.workflow import retry_failed_jobs, retry_publish_job
from wechat_article_scheduler.publish_config import (
    defaults_from_rules,
    human_publish_config_summary,
    parse_publish_config,
    publish_config_from_payload,
)
from wechat_article_scheduler.publish_policy import (
    global_publish_policy,
    resolve_effective_submit,
)
from wechat_article_scheduler.content_quality import article_content_hints
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from wechat_article_scheduler.web.covers import (
    batch_set_cover_from_article,
    batch_set_cover_from_bytes,
    batch_set_cover_from_path,
    normalize_cover_config,
    resolve_cover_config,
)
from wechat_article_scheduler.web.uploads import handle_upload, save_cover_file
from wechat_article_scheduler.web.bulk_manage import (
    build_delete_impact,
    bulk_cancel_publish_jobs,
    cancel_publish_job,
    cleanup_orphan_covers,
    list_orphan_covers,
)
from wechat_article_scheduler.web.trash import (
    bulk_restore,
    bulk_soft_delete,
    list_trash_articles,
    purge_trash,
    restore_article,
    soft_delete_article,
)

_TEMPLATE_PATH = Path(__file__).parent / "admin_template.html"
_ADMIN_HTML = _TEMPLATE_PATH.read_text(encoding="utf-8") if _TEMPLATE_PATH.exists() else "<html><body>模板缺失</body></html>"
_DETAIL_TEMPLATE_PATH = Path(__file__).parent / "article_detail_template.html"
_DRAFTS_PAGE_TEMPLATE_PATH = Path(__file__).parent / "drafts_page_template.html"
logger = logging.getLogger(__name__)


def _cover_asset_roots(config: AppConfig) -> list[Path]:
    roots = [config.root / "cover_assets", config.covers_dir, config.root / "assets" / "covers"]
    out: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            out.append(resolved)
    return out


def _is_under_any(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _job_publish_config(row: Any, config: AppConfig):
    raw = None
    try:
        raw = row["publish_config_json"]
    except (IndexError, KeyError):
        pass
    return parse_publish_config(raw, defaults=defaults_from_rules(config))


def _pending_auto_execute_job_count(config: AppConfig) -> int:
    with db.connect(config.database_path) as conn:
        rows = conn.execute(
            """
            SELECT j.publish_config_json
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            """
        ).fetchall()
    count = 0
    for row in rows:
        pub_cfg = _job_publish_config(row, config)
        if pub_cfg.auto_execute:
            count += 1
    return count


def _web_auto_runner_state(config: AppConfig) -> tuple[bool, str]:
    """Web 工作台到点自动执行：仅处理已勾选「到点自动执行」的任务。"""
    if not getattr(config, "web_auto_run_due", False):
        return False, "WEB_AUTO_RUN_DUE=false"
    if config.dry_run:
        return False, "DRY_RUN=true"
    auto_count = _pending_auto_execute_job_count(config)
    if auto_count <= 0:
        return False, "暂无到点自动执行任务"
    if (
        config.wechat_mode == "real"
        and config.wechat_enable_publish
        and not getattr(config, "web_auto_publish", False)
    ):
        return False, "WEB_AUTO_PUBLISH=false，真实发布需手动执行到点"
    return True, f"已开启（{auto_count} 个到点自动执行任务）"


def _pending_publish_job_count(config: AppConfig) -> int:
    with db.connect(config.database_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            WHERE j.status = 'pending'
              AND (a.deleted_at IS NULL OR a.deleted_at = '')
            """
        ).fetchone()
    return int(row["cnt"] if row else 0)


def _runner_task(app: FastAPI) -> asyncio.Task | None:
    task = getattr(app.state, "web_auto_runner_task", None)
    if task is not None and task.done():
        app.state.web_auto_runner_task = None
        return None
    return task


async def _stop_web_auto_runner(app: FastAPI, *, reason: str) -> None:
    task = _runner_task(app)
    current = asyncio.current_task()
    if task is not None and task is not current:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    app.state.web_auto_runner_task = None
    app.state.web_auto_runner_active = False
    app.state.web_auto_runner_reason = reason


async def _sync_web_auto_runner(app: FastAPI, config: AppConfig) -> None:
    allowed, reason = _web_auto_runner_state(config)
    if not allowed:
        await _stop_web_auto_runner(app, reason=reason)
        logger.info("Web 到点自动执行未启动：%s", reason)
        return

    pending_count = _pending_auto_execute_job_count(config)
    if pending_count <= 0:
        await _stop_web_auto_runner(app, reason="暂无到点自动执行任务")
        logger.info("Web 到点自动执行已停止：暂无到点自动执行任务")
        return

    if _runner_task(app) is not None:
        app.state.web_auto_runner_active = True
        app.state.web_auto_runner_reason = f"已开启（{pending_count} 个到点自动执行任务）"
        return

    app.state.web_auto_runner_active = True
    app.state.web_auto_runner_reason = f"已开启（{pending_count} 个到点自动执行任务）"
    app.state.web_auto_runner_task = asyncio.create_task(_web_auto_run_loop(config, app))


async def _web_auto_run_loop(config: AppConfig, app: FastAPI) -> None:
    poll = max(5, config.scheduler_poll_seconds)
    logger.info("Web 到点自动执行已启动：每 %ss 检查一次", poll)
    while True:
        try:
            pending_before = _pending_auto_execute_job_count(config)
            if pending_before <= 0:
                await _stop_web_auto_runner(app, reason="暂无到点自动执行任务")
                return
            stats = run_due_jobs(config, only_auto_execute=True)
            if any(stats.get(k) for k in ("processed", "drafted", "failed", "dry_run")):
                logger.info("Web 到点自动执行结果: %s", stats)
            pending_after = _pending_auto_execute_job_count(config)
            if pending_after <= 0:
                await _stop_web_auto_runner(app, reason="暂无到点自动执行任务")
                return
            app.state.web_auto_runner_active = True
            app.state.web_auto_runner_reason = f"已开启（{pending_after} 个到点自动执行任务）"
        except Exception:  # noqa: BLE001 - 后台循环不应拖垮 Web 工作台
            logger.exception("Web 到点自动执行失败")
        await asyncio.sleep(poll)


def _enrich_job_row(row: dict[str, Any], config: AppConfig) -> dict[str, Any]:
    pub_cfg = parse_publish_config(row.get("publish_config_json"), defaults=defaults_from_rules(config))
    row["publish_config"] = pub_cfg.normalized().__dict__
    row["publish_config_label"] = " · ".join(human_publish_config_summary(pub_cfg))
    eff = resolve_effective_submit(app_config=config, job_config=pub_cfg)
    row["publish_effective"] = eff
    row["publish_effective_badge"] = eff["badge"]
    row["publish_effective_label"] = eff["label"]
    return row


def create_app(config: AppConfig | None = None) -> FastAPI:
    """创建 FastAPI 应用（可注入 config 便于测试）。"""
    cfg = config or load_config()
    # 启动时补齐 schema 与 migrations（旧库可能缺少 deleted_at 等列）
    db.init_db(cfg.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.web_auto_runner_task = None
        app.state.web_auto_runner_active = False
        app.state.web_auto_runner_reason = "未启动"
        await _sync_web_auto_runner(app, cfg)
        try:
            yield
        finally:
            await _stop_web_auto_runner(app, reason="服务已停止")

    app = FastAPI(
        title="微信公众号文章调度器",
        description="本地管理后台（默认 mock）",
        lifespan=lifespan,
    )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        """普通用户工作台首页（Desktop-first）。"""
        return _ADMIN_HTML

    @app.get("/debug", response_class=HTMLResponse)
    def debug_page() -> str:
        """高级排错页：展示原始 JSON 与内部字段。"""
        return _DEBUG_HTML

    @app.get("/articles/{article_id}", response_class=HTMLResponse)
    def article_detail_page(article_id: int) -> str:
        """单篇作品详情与预览（收敛 Round 11）。"""
        if not _DETAIL_TEMPLATE_PATH.is_file():
            raise HTTPException(status_code=500, detail="详情页模板缺失")
        with db.connect(cfg.database_path) as conn:
            if build_article_detail(cfg, conn, article_id) == {}:
                raise HTTPException(status_code=404, detail="作品不存在")
        html = _DETAIL_TEMPLATE_PATH.read_text(encoding="utf-8")
        return html.replace("{{ARTICLE_ID}}", str(int(article_id)))

    @app.get("/api/articles/{article_id}")
    def article_detail_api(article_id: int) -> dict[str, Any]:
        """单篇作品详情 JSON（排期、草稿、预检、下一步）。"""
        with db.connect(cfg.database_path) as conn:
            detail = build_article_detail(cfg, conn, article_id)
        if not detail:
            raise HTTPException(status_code=404, detail="作品不存在")
        return detail

    @app.post("/api/articles/{article_id}/update-draft")
    async def article_update_draft(article_id: int) -> dict[str, Any]:
        """将当前作品内容同步到已有微信草稿（draft/update）。"""
        result = update_article_wechat_draft(cfg, article_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
        result.setdefault("human", humanize_update_result(result))
        return result

    @app.post("/api/articles/{article_id}/export-outbox")
    def article_export_outbox(article_id: int, platform: str = "generic") -> dict[str, Any]:
        """导出 manual_export outbox 包（不联网、不标记已发布）。"""
        with db.connect(cfg.database_path) as conn:
            result = export_article_to_outbox(
                cfg, conn, article_id, platform=(platform or "generic").strip()
            )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "导出失败"))
        return result

    @app.get("/api/outbox-packages")
    def api_outbox_packages(limit: int = 30) -> dict[str, Any]:
        items = list_outbox_packages(cfg, limit=min(max(limit, 1), 100))
        return {"count": len(items), "items": items}

    @app.get("/api/manual-export/platforms")
    def api_manual_export_platforms() -> dict[str, Any]:
        """manual_export 支持的平台列表（不联网）。"""
        return {
            "platforms": [
                {"id": k, **v} for k, v in SUPPORTED_PLATFORMS.items()
            ]
        }

    @app.get("/api/wechat-field-matrix")
    def api_wechat_field_matrix() -> dict[str, Any]:
        """微信公众号字段能力矩阵（Round 17）。"""
        return {
            "summary": matrix_summary(),
            "fields": list_field_matrix(),
            "gaps": field_gaps(),
        }

    @app.get("/api/browser-assist-plan")
    def api_browser_assist_plan(
        article_id: str | None = None,
        media_id: str | None = None,
        platform: str = "wechat_official",
    ) -> dict[str, Any]:
        """browser_assist 干跑计划（人机确认，不自动发布）。"""
        try:
            return build_dry_run_plan(
                platform=platform,
                article_id=article_id,
                media_id=media_id,
                config=cfg,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/browser-assist/platforms")
    def api_browser_assist_platforms() -> dict[str, Any]:
        return {
            "platforms": [{"id": k, **v} for k, v in SUPPORTED_BROWSER_ASSIST.items()],
        }

    @app.get("/api/adapter-registry")
    def api_adapter_registry(
        platform: str | None = None,
        adapter_type: str | None = None,
    ) -> dict[str, Any]:
        from wechat_article_scheduler.adapters.registry import list_adapter_capabilities

        caps = list_adapter_capabilities(platform=platform, adapter_type=adapter_type)
        return {"count": len(caps), "capabilities": caps}

    @app.get("/api/local-blog/destinations")
    def api_local_blog_destinations() -> dict[str, Any]:
        from wechat_article_scheduler.adapters.local_blog.plans import list_destinations

        items = list_destinations()
        return {"count": len(items), "destinations": items}

    @app.get("/api/local-blog-plan")
    def api_local_blog_plan(
        destination: str = "static_site",
        article_id: str | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        from wechat_article_scheduler.adapters.local_blog.plans import build_plan

        try:
            return build_plan(
                destination=destination,
                article_id=article_id,
                output_dir=output_dir,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/webhook/channels")
    def api_webhook_channels() -> dict[str, Any]:
        from wechat_article_scheduler.adapters.webhook.plans import list_channels

        items = list_channels()
        return {"count": len(items), "channels": items}

    @app.get("/api/video-package/platforms")
    def api_video_package_platforms() -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.video_presearch import (
            list_video_platforms,
        )

        items = list_video_platforms()
        return {"count": len(items), "platforms": items}

    @app.get("/api/video-package-plan")
    def api_video_package_plan(
        platform: str = "bilibili",
        package_id: str | None = None,
        title: str | None = None,
        video_path: str | None = None,
    ) -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.video_presearch import (
            build_video_package_dry_run,
        )

        try:
            return build_video_package_dry_run(
                platform=platform,
                package_id=package_id,
                title=title,
                video_path=video_path,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/audio-package/platforms")
    def api_audio_package_platforms() -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.audio_presearch import (
            list_audio_platforms,
        )

        items = list_audio_platforms()
        return {"count": len(items), "platforms": items}

    @app.get("/api/audio-package-plan")
    def api_audio_package_plan(
        platform: str = "podcast",
        package_id: str | None = None,
        title: str | None = None,
        audio_path: str | None = None,
    ) -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.audio_presearch import (
            build_audio_package_dry_run,
        )

        try:
            return build_audio_package_dry_run(
                platform=platform,
                package_id=package_id,
                title=title,
                audio_path=audio_path,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/short-video/platforms")
    def api_short_video_platforms() -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.short_video_deferred import (
            list_short_video_platforms,
        )

        items = list_short_video_platforms()
        return {"count": len(items), "platforms": items}

    @app.get("/api/short-video-plan")
    def api_short_video_plan(
        platform: str = "douyin",
        article_id: str | None = None,
    ) -> dict[str, Any]:
        from wechat_article_scheduler.content_packages.short_video_deferred import (
            build_short_video_deferred_plan,
        )

        try:
            return build_short_video_deferred_plan(
                platform=platform,
                article_id=article_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/wechat-chain-summary")
    def api_wechat_chain_summary() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            from wechat_article_scheduler.wechat_chain_summary import (
                build_wechat_chain_summary,
            )

            return build_wechat_chain_summary(cfg, conn)

    @app.get("/api/webhook-plan")
    def api_webhook_plan(
        channel: str = "generic",
        article_id: str | None = None,
        event_type: str = "article.ready",
    ) -> dict[str, Any]:
        from wechat_article_scheduler.adapters.webhook.plans import build_plan

        try:
            return build_plan(
                channel=channel,
                article_id=article_id,
                event_type=event_type,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/manifest/sample-dry-run")
    def api_manifest_sample_dry_run() -> dict[str, Any]:
        from pathlib import Path

        from wechat_article_scheduler.content_packages.from_manifest import (
            manifest_dry_run_summary,
        )
        from wechat_article_scheduler.core.manifest_loader import load_manifest

        sample = (
            Path(__file__).resolve().parents[3]
            / "manifests"
            / "examples"
            / "sample_publish_manifest.json"
        )
        if not sample.is_file():
            raise HTTPException(status_code=404, detail="示例 manifest 不存在")
        return manifest_dry_run_summary(load_manifest(sample))

    @app.get("/api/waiting-confirmation")
    def api_waiting_confirmation() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            items = list_waiting_confirmation(conn)
        return {"count": len(items), "items": items}

    @app.get("/api/publish-jobs/{job_id}/proof")
    def api_get_publish_proof(job_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            proof = get_proof_for_job(conn, job_id)
        if not proof:
            return {"ok": True, "proof": None}
        return {"ok": True, "proof": proof}

    @app.post("/api/publish-jobs/{job_id}/proof")
    def api_submit_publish_proof(job_id: int, body: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        proof = ProofInput(
            screenshot_path=body.get("screenshot_path"),
            public_url=body.get("public_url"),
            confirmed_by=body.get("confirmed_by"),
            note=body.get("note"),
        )
        with db.connect(cfg.database_path) as conn:
            result = submit_publish_proof(conn, job_id, proof)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "提交失败"))
        return result

    @app.post("/api/publish-jobs/{job_id}/waiting-confirmation")
    def api_mark_waiting_confirmation(job_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            result = mark_job_waiting_confirmation(conn, job_id)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))
        return result

    @app.get("/api/user-labels")
    def user_labels() -> dict[str, Any]:
        return export_labels_json()

    @app.get("/api/status")
    def status() -> dict[str, Any]:
        return {
            "wechat_mode": cfg.wechat_mode,
            "dry_run": cfg.dry_run,
            "wechat_enable_publish": cfg.wechat_enable_publish,
            "publish_policy": global_publish_policy(cfg),
            "web_auto_run_due": cfg.web_auto_run_due,
            "web_auto_publish": cfg.web_auto_publish,
            "web_auto_runner_active": bool(getattr(app.state, "web_auto_runner_active", False)),
            "web_auto_runner_reason": str(getattr(app.state, "web_auto_runner_reason", "")),
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
                       j.adapter_mode, j.updated_at, j.publish_config_json, a.title
                FROM publish_jobs j
                JOIN articles a ON a.id = j.article_id
                WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
                ORDER BY j.updated_at DESC, j.id DESC
                LIMIT 10
                """
            ).fetchall()
            schedule = summarize_schedule(conn)
            preflight = build_publish_preflight(cfg, conn)
            from wechat_article_scheduler.wechat_chain_summary import build_wechat_chain_summary

            chain_summary = build_wechat_chain_summary(cfg, conn)
        recent_jobs_out = []
        for r in recent_jobs:
            row = _enrich_job_row(dict(r), cfg)
            row["scheduled_at_label"] = format_scheduled_at(row.get("scheduled_at"))
            recent_jobs_out.append(row)
        article_counts = {str(r["status"]): int(r["count"]) for r in article_rows}
        job_counts = {str(r["status"]): int(r["count"]) for r in job_rows}
        workbench = build_workbench_hints(
            article_counts=article_counts,
            job_counts=job_counts,
            schedule_summary=schedule,
            chain_summary=chain_summary,
        )
        return {
            "status": status(),
            "article_counts": article_counts,
            "job_counts": job_counts,
            "recent_jobs": recent_jobs_out,
            "recent_events": [dict(r) for r in list_events(cfg, limit=10)],
            "schedule_summary": schedule,
            "workbench": workbench,
            "publish_preflight": preflight,
            "wechat_chain_summary": chain_summary,
            "docs": [
                {"label": "README", "path": "README.md"},
                {"label": "开发路线图", "path": "docs/rounds.md"},
                {"label": "Web 控制台设计", "path": "docs/web_console_design.md"},
            ],
        }

    @app.get("/api/articles")
    def articles(
        limit: int = 50,
        collection_slug: str | None = None,
        collection: str | None = None,
    ) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            sql = """
                SELECT a.id, a.title, a.summary, a.body, a.status, a.source_path, a.cover_path,
                       a.cover_config_json, a.created_at, a.updated_at,
                       COALESCE(c.slug, 'default') AS collection_slug,
                       COALESCE(c.name, '默认集合') AS collection_name,
                       EXISTS(
                           SELECT 1 FROM wechat_drafts d WHERE d.article_id = a.id
                       ) AS has_wechat_draft,
                       (
                           SELECT j.status FROM publish_jobs j
                           WHERE j.article_id = a.id
                           ORDER BY j.id DESC LIMIT 1
                       ) AS latest_job_status
                FROM articles a
                LEFT JOIN collections c ON c.id = a.collection_id
                WHERE (a.deleted_at IS NULL OR a.deleted_at = '')
            """
            params: list[Any] = []
            slug_filter = (collection_slug or collection or "").strip()
            if slug_filter:
                sql += " AND COALESCE(c.slug, 'default') = ?"
                params.append(slug_filter)
            sql += " ORDER BY a.id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            row = dict(r)
            row["has_cover"] = bool((row.get("cover_path") or "").strip())
            row["has_summary"] = bool((row.get("summary") or "").strip())
            row["has_cover_config"] = bool((row.get("cover_config_json") or "").strip())
            row["cover_url"] = f"/media/cover/{row['id']}" if row["has_cover"] else None
            row["has_wechat_draft"] = bool(row.get("has_wechat_draft"))
            row["workflow_hint"] = article_workflow_hint(
                status=row.get("status"),
                latest_job_status=row.get("latest_job_status"),
                has_wechat_draft=row["has_wechat_draft"],
            )
            row["content_hints"] = article_content_hints(
                row.get("title") or "",
                row.get("body") or "",
            )
            out.append(row)
        return out

    @app.get("/api/trash")
    def trash_list(limit: int = 50) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            return list_trash_articles(conn, limit=limit)

    @app.post("/api/articles/{article_id}/trash")
    async def trash_article(article_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            if not soft_delete_article(conn, article_id):
                raise HTTPException(status_code=404, detail="作品不存在或已在回收站")
            conn.commit()
        await _sync_web_auto_runner(app, cfg)
        return {"ok": True, "article_id": article_id, "human": ["作品已移入回收站，相关待发布任务已取消"]}

    @app.post("/api/articles/{article_id}/restore")
    def restore_trashed_article(article_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            if not restore_article(conn, article_id):
                raise HTTPException(status_code=404, detail="回收站中未找到该作品")
            conn.commit()
        return {"ok": True, "article_id": article_id, "human": ["作品已从回收站恢复"]}

    @app.post("/api/articles/bulk-trash")
    async def bulk_trash_articles(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        ids = [int(x) for x in (payload.get("ids") or [])]
        with db.connect(cfg.database_path) as conn:
            stats = bulk_soft_delete(conn, ids)
            conn.commit()
        await _sync_web_auto_runner(app, cfg)
        return {"ok": True, **stats, "human": [f"已移入回收站 {stats['deleted']} 篇"]}

    @app.post("/api/articles/bulk-restore")
    def bulk_restore_articles(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        ids = [int(x) for x in (payload.get("ids") or [])]
        with db.connect(cfg.database_path) as conn:
            stats = bulk_restore(conn, ids)
            conn.commit()
        return {"ok": True, **stats, "human": [f"已恢复 {stats['restored']} 篇"]}

    @app.post("/api/trash/purge")
    async def purge_trash_bin() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            result = purge_trash(cfg, conn)
            conn.commit()
        await _sync_web_auto_runner(app, cfg)
        return {
            "ok": True,
            **result,
            "human": [f"已彻底删除 {result['purged']} 篇回收站作品"],
        }

    @app.post("/api/articles/delete-preview")
    async def delete_impact_preview(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        ids = [int(x) for x in (payload.get("ids") or [])]
        with db.connect(cfg.database_path) as conn:
            impact = build_delete_impact(conn, ids)
        return {"ok": True, **impact}

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            if not cancel_publish_job(conn, job_id):
                raise HTTPException(status_code=404, detail="任务不存在或无法取消")
            conn.commit()
        await _sync_web_auto_runner(app, cfg)
        return {"ok": True, "job_id": job_id, "human": ["已取消该待发布任务"]}

    @app.post("/api/jobs/bulk-cancel")
    async def bulk_cancel_jobs(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        job_ids = [int(x) for x in (payload.get("job_ids") or [])]
        with db.connect(cfg.database_path) as conn:
            stats = bulk_cancel_publish_jobs(conn, job_ids=job_ids)
            conn.commit()
        await _sync_web_auto_runner(app, cfg)
        return {
            "ok": True,
            **stats,
            "human": [f"已取消 {stats['cancelled']} 个待发布任务"],
        }

    @app.get("/api/covers/orphans")
    def covers_orphans() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            items = list_orphan_covers(cfg, conn)
        return {"count": len(items), "orphans": items}

    @app.post("/api/covers/cleanup-orphans")
    async def covers_cleanup_orphans() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            result = cleanup_orphan_covers(cfg, conn)
            conn.commit()
        return {"ok": True, **result}

    @app.get("/api/covers/scan")
    def covers_scan() -> dict[str, Any]:
        """扫描封面素材库、绑定状态与孤儿文件。"""
        with db.connect(cfg.database_path) as conn:
            return scan_cover_assets(cfg, conn)

    @app.post("/api/covers/bind")
    async def covers_bind_stems() -> dict[str, Any]:
        """按作品文件名 stem 自动绑定磁盘封面。"""
        with db.connect(cfg.database_path) as conn:
            result = bind_covers_by_stem(cfg, conn)
        return {"ok": True, **result}

    @app.post("/api/covers/repair")
    async def covers_repair_paths() -> dict[str, Any]:
        """清除指向不存在文件的 cover_path。"""
        with db.connect(cfg.database_path) as conn:
            result = repair_invalid_cover_paths(cfg, conn)
        return {"ok": True, **result}

    @app.get("/api/jobs")
    def jobs(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            return list_queue_jobs(conn, cfg, limit=limit, status=status)

    @app.get("/api/queue-summary")
    def api_queue_summary() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            return queue_summary(conn)

    @app.get("/drafts", response_class=HTMLResponse)
    def drafts_page() -> str:
        path = _DRAFTS_PAGE_TEMPLATE_PATH
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "<html><body>草稿页模板缺失</body></html>"

    @app.get("/api/drafts")
    def api_drafts(limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        with db.connect(cfg.database_path) as conn:
            return list_wechat_drafts(conn, cfg, limit=limit, status=status)

    @app.get("/api/drafts-summary")
    def api_drafts_summary() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            return drafts_summary(conn, cfg)

    @app.get("/api/drafts/{draft_id}")
    def api_draft_detail(draft_id: int) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            detail = get_wechat_draft(conn, cfg, draft_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="草稿记录不存在")
        return detail

    @app.post("/api/jobs/{job_id}/retry")
    async def retry_job(job_id: int) -> dict[str, Any]:
        if not retry_publish_job(cfg, job_id):
            raise HTTPException(status_code=404, detail="任务不存在或不是失败状态")
        await _sync_web_auto_runner(app, cfg)
        return {
            "ok": True,
            "job_id": job_id,
            "retried": 1,
            "human": humanize_retry_jobs_result({"retried": 1}),
        }

    @app.post("/api/jobs/bulk-retry")
    async def bulk_retry_jobs(payload: dict[str, Any] = Body(default={})) -> dict[str, Any]:
        job_ids = [int(x) for x in (payload.get("job_ids") or [])]
        if payload.get("retry_all"):
            count = retry_failed_jobs(cfg)
        elif job_ids:
            count = retry_failed_jobs(cfg, job_ids)
        else:
            count = retry_failed_jobs(cfg)
        await _sync_web_auto_runner(app, cfg)
        return {
            "ok": True,
            "retried": count,
            "human": humanize_retry_jobs_result({"retried": count}),
        }

    @app.get("/api/publish-preflight")
    def publish_preflight() -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            return build_publish_preflight(cfg, conn)

    @app.get("/api/schedule-summary")
    def schedule_summary(limit: int = 10) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            return summarize_schedule(conn, limit=limit)

    @app.get("/api/events")
    def events(limit: int = 30) -> list[dict[str, Any]]:
        rows = list_events(cfg, limit=limit)
        return [dict(r) for r in rows]

    @app.post("/api/upload")
    async def upload(
        articles: list[UploadFile] = File(default=[]),
        covers: list[UploadFile] = File(default=[]),
    ) -> dict[str, Any]:
        """批量上传作品文件与封面图（multipart）。"""
        article_payloads = [(f.filename or "unnamed", await f.read()) for f in articles]
        cover_payloads = [(f.filename or "unnamed", await f.read()) for f in covers]
        return handle_upload(cfg, articles=article_payloads, covers=cover_payloads)

    @app.post("/api/articles/{article_id}/cover")
    async def set_article_cover(
        article_id: int,
        cover: UploadFile = File(...),
        cover_config_json: str | None = Form(default=None),
    ) -> dict[str, Any]:
        """为单篇作品替换/设置封面。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute("SELECT id, title FROM articles WHERE id = ?", (article_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="作品不存在")
        data = await cover.read()
        dest = save_cover_file(cfg, cover.filename or f"cover_{article_id}.png", data)
        cfg_json: str | None = None
        if cover_config_json:
            try:
                cfg_json = normalize_cover_config(cover_config_json)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        with db.connect(cfg.database_path) as conn:
            conn.execute(
                """
                UPDATE articles
                SET cover_path = ?, cover_config_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (str(dest), cfg_json, article_id),
            )
            conn.commit()
        return {
            "article_id": article_id,
            "cover_url": f"/media/cover/{article_id}",
            "human": [f"《{row['title'] or '无标题'}》的封面已更新"],
        }

    @app.post("/api/articles/batch-cover")
    async def batch_set_covers(
        ids: str = Form(...),
        cover: UploadFile | None = File(default=None),
        cover_asset_path: str | None = Form(default=None),
        copy_from_article_id: int | None = Form(default=None),
        reuse_config_from_article_id: int | None = Form(default=None),
        cover_config_json: str | None = Form(default=None),
    ) -> dict[str, Any]:
        """批量为选中作品设置封面，可选复用封面裁剪位置。"""
        try:
            raw_ids = json.loads(ids)
            article_ids = [int(x) for x in raw_ids]
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="ids 必须是 JSON 数组") from exc
        if not article_ids:
            raise HTTPException(status_code=400, detail="请至少选择一篇作品")

        with db.connect(cfg.database_path) as conn:
            try:
                cfg_json = resolve_cover_config(
                    conn,
                    explicit=cover_config_json,
                    reuse_from_article_id=reuse_config_from_article_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            try:
                if cover is not None and cover.filename:
                    data = await cover.read()
                    stats = batch_set_cover_from_bytes(
                        cfg,
                        conn,
                        article_ids,
                        filename=cover.filename or "batch_cover.png",
                        data=data,
                        cover_config_json=cfg_json,
                    )
                elif copy_from_article_id is not None:
                    stats = batch_set_cover_from_article(
                        conn,
                        article_ids,
                        source_article_id=copy_from_article_id,
                        cover_config_json=cfg_json,
                    )
                elif cover_asset_path:
                    asset = Path(cover_asset_path)
                    if not asset.is_file():
                        raise HTTPException(status_code=400, detail="封面素材路径无效")
                    stats = batch_set_cover_from_path(
                        conn,
                        article_ids,
                        cover_path=str(asset),
                        cover_config_json=cfg_json,
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail="请上传封面、选择素材库文件或指定源作品",
                    )
            except FileNotFoundError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            conn.commit()

        msg = f"已为 {stats['updated']} 篇作品设置封面"
        if stats["skipped"]:
            msg += f"（跳过 {stats['skipped']} 篇）"
        if cfg_json:
            msg += "，并已应用封面位置配置"
        return {"ok": True, **stats, "human": [msg]}

    @app.get("/api/articles/{article_id}/cover-previews")
    def article_cover_previews(article_id: int) -> dict[str, Any]:
        """横向 2.35:1 与方形 1:1 封面预览（Pillow 可选）。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                """
                SELECT cover_path, cover_config_json
                FROM articles WHERE id = ?
                """,
                (article_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        cover_path = (row["cover_path"] or "").strip()
        if not cover_path or not Path(cover_path).is_file():
            raise HTTPException(status_code=404, detail="封面不存在")
        result = build_dual_cover_previews(cover_path, row["cover_config_json"])
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "预览失败"))
        return result

    @app.post("/api/cover-preview/dual")
    async def cover_preview_dual(
        cover_path: str = Form(...),
        cover_config_json: str | None = Form(default=None),
    ) -> dict[str, Any]:
        """按路径与裁剪配置生成双比例预览（批量封面弹窗可用）。"""
        path = Path(cover_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail="封面路径无效")
        allowed_roots = _cover_asset_roots(cfg) + [cfg.covers_dir.resolve()]
        if not _is_under_any(path.resolve(), allowed_roots):
            raise HTTPException(status_code=400, detail="封面路径不在允许目录")
        cfg_json = None
        if cover_config_json:
            cfg_json = enrich_cover_config(cover_config_json)
        result = build_dual_cover_previews(path, cfg_json)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "预览失败"))
        return result

    @app.get("/media/cover/{article_id}")
    def media_cover(article_id: int) -> FileResponse:
        """返回作品封面图（仅本地文件）。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                "SELECT cover_path FROM articles WHERE id = ?", (article_id,)
            ).fetchone()
        cover_path = (row["cover_path"] if row else None) or ""
        path = Path(cover_path)
        if not cover_path or not path.is_file():
            raise HTTPException(status_code=404, detail="封面不存在")
        return FileResponse(str(path))

    @app.get("/media/cover-asset")
    def media_cover_asset(path: str) -> FileResponse:
        """返回封面素材库中的素材（供控制台裁剪预览）。"""
        asset = Path(path).resolve()
        if not _is_under_any(asset, _cover_asset_roots(cfg)):
            raise HTTPException(status_code=400, detail="封面素材路径无效")
        if not asset.is_file():
            raise HTTPException(status_code=404, detail="封面素材不存在")
        return FileResponse(str(asset))

    @app.post("/api/scan")
    def trigger_scan() -> dict[str, Any]:
        result = scan_inbox(cfg)
        result["human"] = humanize_scan_result(result)
        return result

    @app.post("/api/plan")
    async def trigger_plan() -> dict[str, Any]:
        result = build_plan(cfg)
        result["human"] = humanize_plan_result(result)
        await _sync_web_auto_runner(app, cfg)
        return result

    @app.post("/api/articles/{article_id}/schedule")
    async def schedule_article(
        article_id: int,
        payload: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        raw = str(payload.get("scheduled_at") or "").strip()
        try:
            when = parse_scheduled_at(raw)
            pub_cfg = publish_config_from_payload(payload)
            result = assign_article_schedule(cfg, article_id, when, publish_config=pub_cfg)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["ok"] = True
        result["scheduled_at_label"] = format_scheduled_at(result["scheduled_at"])
        result["human"] = humanize_schedule_single_result(result)
        await _sync_web_auto_runner(app, cfg)
        return result

    @app.post("/api/articles/batch-schedule")
    async def batch_schedule(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        ids = [int(x) for x in (payload.get("ids") or [])]
        raw_anchor = str(payload.get("anchor_at") or "").strip()
        sort_order = str(payload.get("sort_order") or "asc").strip().lower()
        interval = int(payload.get("interval") or 5)
        interval_unit = str(payload.get("interval_unit") or "minutes").strip().lower()
        if sort_order not in ("asc", "desc"):
            raise HTTPException(status_code=400, detail="排序方式无效")
        if interval_unit not in ("minutes", "hours"):
            raise HTTPException(status_code=400, detail="间隔单位无效")
        try:
            anchor = parse_scheduled_at(raw_anchor)
            pub_cfg = publish_config_from_payload(payload)
            stats = assign_batch_schedule(
                cfg,
                ids,
                anchor=anchor,
                sort_order=sort_order,  # type: ignore[arg-type]
                interval=interval,
                interval_unit=interval_unit,  # type: ignore[arg-type]
                publish_config=pub_cfg,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        msg_stats = {**stats, "human": humanize_schedule_batch_result(stats)}
        await _sync_web_auto_runner(app, cfg)
        return {"ok": True, **msg_stats}

    @app.post("/api/run-once")
    async def trigger_run_once() -> dict[str, Any]:
        result = run_due_jobs(cfg)
        result["human"] = humanize_run_once_result(result)
        await _sync_web_auto_runner(app, cfg)
        return result

    @app.get("/api/cover-assets")
    def cover_assets_index() -> dict[str, Any]:
        roots = _cover_asset_roots(cfg)
        indexed = []
        seen_paths: set[str] = set()
        for root in roots:
            for asset in index_cover_directory(root):
                if asset.path in seen_paths:
                    continue
                seen_paths.add(asset.path)
                indexed.append({"asset": asset, "source": str(root)})
        check = check_cover_path(
            None,
            default_thumb=Path(cfg.wechat_default_thumb_path)
            if cfg.wechat_default_thumb_path
            else None,
        )
        with db.connect(cfg.database_path) as conn:
            scan = scan_cover_assets(cfg, conn)
        return {
            "directory": str(roots[0]),
            "directories": [str(root) for root in roots],
            "assets": [
                {
                    "path": item["asset"].path,
                    "name": item["asset"].name,
                    "size_bytes": item["asset"].size_bytes,
                    "source": item["source"],
                }
                for item in indexed
            ],
            "publish_check": check,
            "scan_summary": {
                "asset_count": scan["asset_count"],
                "missing_cover_count": scan["missing_cover_count"],
                "broken_binding_count": scan["broken_binding_count"],
                "bindable_count": scan["bindable_count"],
                "orphan_count": scan["orphan_count"],
                "human": scan["human"],
            },
        }

    @app.get("/api/collections")
    def collections_api() -> dict[str, Any]:
        """合集列表（含作品计数，同步 collection.yaml）。"""
        with db.connect(cfg.database_path) as conn:
            sync_discovered_collections(cfg, conn)
            conn.commit()
            rows = list_collections_summary(conn)
        discovered = len(discover_collection_configs(cfg.root))
        return {
            "discovered_yaml": discovered,
            "collections": rows,
            "human": [f"已注册 {len(rows)} 个合集（YAML 定义 {discovered} 个）"],
        }

    @app.get("/api/content-library")
    def content_library_view(
        collection: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        with db.connect(cfg.database_path) as conn:
            sync_discovered_collections(cfg, conn)
            conn.commit()
            items = list_content_items(
                conn,
                limit=limit,
                collection_slug=collection,
            )
            collections = list_collections_summary(conn)
        return {
            "collections": collections,
            "items": [
                {
                    "article_id": i.article_id,
                    "title": i.title,
                    "collection_slug": i.collection_slug,
                    "tags": list(i.tags),
                }
                for i in items
            ],
        }

    @app.get("/api/articles/{article_id}/render-preview")
    def article_render_preview(article_id: int, save_snapshot: bool = False) -> dict[str, Any]:
        """公众号效果预览（与 draft/add 同源 HTML；可选落盘快照）。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, title, summary, body, cover_path
                FROM articles WHERE id = ?
                """,
                (article_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        package = build_article_preview_package(cfg, row, article_id=article_id)
        if save_snapshot:
            path = save_preview_snapshot(cfg, package)
            package["snapshot_path"] = str(path.relative_to(cfg.root))
        latest = latest_snapshot_path(cfg, article_id)
        if latest is not None:
            package["latest_snapshot"] = str(latest.relative_to(cfg.root))
        return package

    @app.post("/api/articles/{article_id}/preview-snapshot")
    def article_preview_snapshot_save(article_id: int) -> dict[str, Any]:
        """显式保存预览快照到 storage/preview_snapshots/。"""
        with db.connect(cfg.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, title, summary, body, cover_path
                FROM articles WHERE id = ?
                """,
                (article_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        package = build_article_preview_package(cfg, row, article_id=article_id)
        path = save_preview_snapshot(cfg, package)
        return {
            "ok": True,
            "snapshot_path": str(path.relative_to(cfg.root)),
            "article_id": article_id,
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
<h2>微信字段能力矩阵</h2><pre id="fields">加载中…</pre>
<h2>browser_assist 干跑计划（微信）</h2><pre id="browser-assist">加载中…</pre>
<h2>知乎 browser_assist 评估</h2><pre id="browser-assist-zhihu">加载中…</pre>
<h2>豆瓣 browser_assist 评估</h2><pre id="browser-assist-douban">加载中…</pre>
<h2>Bilibili browser_assist 评估</h2><pre id="browser-assist-bilibili">加载中…</pre>
<h2>小红书 browser_assist 评估</h2><pre id="browser-assist-xhs">加载中…</pre>
<h2>微信视频号 browser_assist 评估</h2><pre id="browser-assist-channels">加载中…</pre>
<h2>Adapter Registry</h2><pre id="adapter-registry">加载中…</pre>
<h2>publish_manifest 干跑（示例）</h2><pre id="manifest-dry-run">加载中…</pre>
<h2>local_blog 评估（静态站）</h2><pre id="local-blog-static">加载中…</pre>
<h2>local_blog 评估（WordPress）</h2><pre id="local-blog-wp">加载中…</pre>
<h2>Webhook 评估（generic）</h2><pre id="webhook-plan">加载中…</pre>
<h2>Phase3 视频内容包预研</h2><pre id="video-package">加载中…</pre>
<h2>微信闭环链路摘要</h2><pre id="wechat-chain">加载中…</pre>
<h2>抖音 deferred 评估</h2><pre id="short-video-douyin">加载中…</pre>
<h2>快手 deferred 评估</h2><pre id="short-video-kuaishou">加载中…</pre>
<h2>Phase4 播客音频预研</h2><pre id="audio-package-podcast">加载中…</pre>
<h2>Phase4 网易云 deferred</h2><pre id="audio-package-netease">加载中…</pre>
<h2>待人工确认队列</h2><pre id="waiting">加载中…</pre>
<h2>outbox 导出包</h2><pre id="outbox">加载中…</pre>
<script>
Promise.all([
  fetch('/api/status'),
  fetch('/api/overview'),
  fetch('/api/wechat-field-matrix'),
  fetch('/api/browser-assist-plan'),
  fetch('/api/browser-assist-plan?platform=zhihu'),
  fetch('/api/browser-assist-plan?platform=douban'),
  fetch('/api/browser-assist-plan?platform=bilibili'),
  fetch('/api/browser-assist-plan?platform=xiaohongshu'),
  fetch('/api/browser-assist-plan?platform=wechat_channels'),
  fetch('/api/adapter-registry'),
  fetch('/api/manifest/sample-dry-run'),
  fetch('/api/local-blog-plan?destination=static_site'),
  fetch('/api/local-blog-plan?destination=wordpress'),
  fetch('/api/webhook-plan?channel=generic'),
  fetch('/api/video-package-plan?platform=bilibili'),
  fetch('/api/wechat-chain-summary'),
  fetch('/api/short-video-plan?platform=douyin'),
  fetch('/api/short-video-plan?platform=kuaishou'),
  fetch('/api/audio-package-plan?platform=podcast'),
  fetch('/api/audio-package-plan?platform=netease_music'),
  fetch('/api/waiting-confirmation'),
  fetch('/api/outbox-packages'),
]).then(async ([a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v])=>{
  document.getElementById('status').textContent = JSON.stringify(await a.json(), null, 2);
  document.getElementById('overview').textContent = JSON.stringify(await b.json(), null, 2);
  document.getElementById('fields').textContent = JSON.stringify(await c.json(), null, 2);
  document.getElementById('browser-assist').textContent = JSON.stringify(await d.json(), null, 2);
  document.getElementById('browser-assist-zhihu').textContent = JSON.stringify(await e.json(), null, 2);
  document.getElementById('browser-assist-douban').textContent = JSON.stringify(await f.json(), null, 2);
  document.getElementById('browser-assist-bilibili').textContent = JSON.stringify(await g.json(), null, 2);
  document.getElementById('browser-assist-xhs').textContent = JSON.stringify(await h.json(), null, 2);
  document.getElementById('browser-assist-channels').textContent = JSON.stringify(await i.json(), null, 2);
  document.getElementById('adapter-registry').textContent = JSON.stringify(await j.json(), null, 2);
  document.getElementById('manifest-dry-run').textContent = JSON.stringify(await k.json(), null, 2);
  document.getElementById('local-blog-static').textContent = JSON.stringify(await l.json(), null, 2);
  document.getElementById('local-blog-wp').textContent = JSON.stringify(await m.json(), null, 2);
  document.getElementById('webhook-plan').textContent = JSON.stringify(await n.json(), null, 2);
  document.getElementById('video-package').textContent = JSON.stringify(await o.json(), null, 2);
  document.getElementById('wechat-chain').textContent = JSON.stringify(await p.json(), null, 2);
  document.getElementById('short-video-douyin').textContent = JSON.stringify(await q.json(), null, 2);
  document.getElementById('short-video-kuaishou').textContent = JSON.stringify(await r.json(), null, 2);
  document.getElementById('audio-package-podcast').textContent = JSON.stringify(await s.json(), null, 2);
  document.getElementById('audio-package-netease').textContent = JSON.stringify(await t.json(), null, 2);
  document.getElementById('waiting').textContent = JSON.stringify(await u.json(), null, 2);
  document.getElementById('outbox').textContent = JSON.stringify(await v.json(), null, 2);
});
</script></body></html>"""
