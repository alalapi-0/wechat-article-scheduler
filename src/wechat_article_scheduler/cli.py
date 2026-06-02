"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from wechat_article_scheduler import db
from wechat_article_scheduler.config import load_config
from wechat_article_scheduler.logging_setup import setup_logging
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.content_cli import print_content_library
from wechat_article_scheduler.events_cli import list_events
from wechat_article_scheduler.scheduler import run_due_jobs, scheduler_loop
from wechat_article_scheduler.scheduler.health import print_scheduler_health
from wechat_article_scheduler.draft_update import update_article_wechat_draft
from wechat_article_scheduler.workflow import reject_article, retry_failed_jobs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="微信公众号文章本地调度器（默认 mock）")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="初始化 SQLite 表结构")
    sub.add_parser("scan", help="扫描 articles/inbox 并导入")
    sub.add_parser("plan", help="为已导入文章生成发布计划")
    sub.add_parser("run-once", help="执行所有已到期的发布任务")
    sub.add_parser("scheduler", help="后台轮询调度（阻塞）")
    sub.add_parser(
        "scheduler-daemon",
        help="常驻调度（同 scheduler；见 docs/scheduler_runbook.md）",
    )
    sub.add_parser("scheduler-health", help="调度器健康检查（队列/锁/卡住任务）")
    sub.add_parser("field-matrix", help="输出微信公众号字段能力矩阵 JSON")
    ba_plan = sub.add_parser(
        "browser-assist-plan",
        help="输出 browser_assist 干跑计划 JSON（人机确认，不自动发布）",
    )
    ba_plan.add_argument("--article-id", type=str, default=None)
    ba_plan.add_argument("--media-id", type=str, default=None)
    ba_plan.add_argument(
        "--platform",
        type=str,
        default="wechat_official",
        help="wechat_official | zhihu | douban | bilibili | xiaohongshu|xhs | wechat_channels|channels",
    )

    sub.add_parser("adapter-registry", help="列出 adapter registry 能力声明 JSON")

    mval = sub.add_parser("manifest-validate", help="校验 publish_manifest.json")
    mval.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="manifest 文件路径",
    )

    mdry = sub.add_parser(
        "manifest-dry-run",
        help="manifest 干跑预览（content_package，不写库）",
    )
    mdry.add_argument("--manifest", type=str, required=True)

    mpdry = sub.add_parser(
        "projects-dry-run",
        help="多项目 projects.yaml 批量 manifest 干跑（不写库）",
    )
    mpdry.add_argument(
        "--projects",
        type=str,
        default=None,
        help="projects.yaml 路径（默认 config/projects.yaml 或 projects.example.yaml）",
    )

    lb = sub.add_parser(
        "local-blog-plan",
        help="local_blog 评估干跑 JSON（静态站/WordPress/本地目录，不真发）",
    )
    lb.add_argument(
        "--destination",
        type=str,
        default="static_site",
        help="static_site | wordpress | local_files",
    )
    lb.add_argument("--article-id", type=str, default=None)
    lb.add_argument("--output-dir", type=str, default=None)

    wh = sub.add_parser("webhook-plan", help="Webhook 评估干跑 JSON（不发起 HTTP）")
    wh.add_argument("--channel", type=str, default="generic", help="generic | feishu | slack")
    wh.add_argument("--article-id", type=str, default=None)
    wh.add_argument("--event-type", type=str, default="article.ready")

    vp = sub.add_parser(
        "video-package-plan",
        help="Phase3 视频内容包预研 dry-run（不上传）",
    )
    vp.add_argument("--platform", type=str, default="bilibili")
    vp.add_argument("--package-id", type=str, default=None)
    vp.add_argument("--title", type=str, default=None)
    vp.add_argument("--video-path", type=str, default=None)

    svp = sub.add_parser(
        "short-video-plan",
        help="抖音/快手 deferred 评估 dry-run（不上传）",
    )
    svp.add_argument("--platform", type=str, default="douyin", help="douyin | kuaishou | ks")
    svp.add_argument("--article-id", type=str, default=None)

    ap = sub.add_parser(
        "audio-package-plan",
        help="Phase4 音频/播客预研 dry-run（不上传）",
    )
    ap.add_argument("--platform", type=str, default="podcast")
    ap.add_argument("--package-id", type=str, default=None)
    ap.add_argument("--title", type=str, default=None)
    ap.add_argument("--audio-path", type=str, default=None)

    sub.add_parser("wechat-chain-summary", help="微信公众号闭环链路摘要 JSON")

    mark_wc = sub.add_parser(
        "mark-waiting-confirmation",
        help="将发布任务标为待人工确认（browser_assist/manual_export）",
    )
    mark_wc.add_argument("--job-id", type=int, required=True)

    submit_proof = sub.add_parser("submit-proof", help="提交发布证明并完成待确认任务")
    submit_proof.add_argument("--job-id", type=int, required=True)
    submit_proof.add_argument("--public-url", type=str, default=None)
    submit_proof.add_argument("--screenshot-path", type=str, default=None)
    submit_proof.add_argument("--confirmed-by", type=str, default=None)
    submit_proof.add_argument("--note", type=str, default=None)

    export_ob = sub.add_parser("export-outbox", help="导出作品为 manual_export outbox 包")
    export_ob.add_argument("--article-id", type=int, required=True)
    export_ob.add_argument(
        "--platform",
        type=str,
        default="generic",
        help="generic | zhihu | douban | bilibili | xiaohongshu | wechat_channels | douyin | kuaishou",
    )

    reject_p = sub.add_parser("reject", help="驳回文章 (Round 1)")
    reject_p.add_argument("--article-id", type=int, required=True)

    sub.add_parser("retry-failed", help="重试失败的发布任务 (Round 1)")

    upd_draft = sub.add_parser("update-draft", help="更新已有微信草稿 (draft/update)")
    upd_draft.add_argument("--article-id", type=int, required=True)

    events_p = sub.add_parser("events", help="列出最近审计事件 (Round 2)")
    events_p.add_argument("--limit", type=int, default=20)

    content_p = sub.add_parser("content", help="列出内容库集合与条目 (Round 2)")
    content_p.add_argument("--limit", type=int, default=20)

    serve_p = sub.add_parser("serve", help="启动 FastAPI 管理后台 (Round 6)")
    serve_p.add_argument("--host", default=None, help="监听地址，默认 WEB_HOST")
    serve_p.add_argument("--port", type=int, default=None, help="端口，默认 WEB_PORT")

    snap_p = sub.add_parser("preview-snapshot", help="生成并保存公众号预览快照 (Round 60)")
    snap_p.add_argument("--article-id", type=int, required=True)

    cover_p = sub.add_parser("cover-scan", help="扫描封面素材库 (Round 61)")
    cover_p.add_argument("--bind", action="store_true", help="按文件名 stem 自动绑定")
    cover_p.add_argument("--repair", action="store_true", help="清除无效 cover_path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = load_config()
    setup_logging(config)

    if args.command == "init-db":
        db.init_db(config.database_path)
        print(f"数据库已初始化: {config.database_path}")
        return 0

    if args.command == "scan":
        stats = scan_inbox(config)
        print(f"扫描完成: {stats}")
        return 0

    if args.command == "plan":
        stats = build_plan(config)
        print(f"计划完成: {stats}")
        return 0

    if args.command == "run-once":
        stats = run_due_jobs(config)
        print(f"执行完成: {stats}")
        return 0

    if args.command in ("scheduler", "scheduler-daemon"):
        if args.command == "scheduler-daemon":
            print(
                "常驻调度已启动（WECHAT_MODE=%s）。停止：Ctrl+C。"
                " 手册：docs/scheduler_runbook.md"
                % config.wechat_mode
            )
        try:
            scheduler_loop(config)
        except KeyboardInterrupt:
            print("\n调度器已停止")
        return 0

    if args.command == "scheduler-health":
        print_scheduler_health(config)
        return 0

    if args.command == "field-matrix":
        import json

        from wechat_article_scheduler.wechat_field_matrix import (
            field_gaps,
            list_field_matrix,
            matrix_summary,
        )

        print(
            json.dumps(
                {
                    "summary": matrix_summary(),
                    "fields": list_field_matrix(),
                    "gaps": field_gaps(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "browser-assist-plan":
        import json

        from wechat_article_scheduler.adapters.browser_assist import build_dry_run_plan

        try:
            plan = build_dry_run_plan(
                platform=args.platform,
                article_id=args.article_id,
                media_id=args.media_id,
                config=config,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "adapter-registry":
        import json

        from wechat_article_scheduler.adapters.registry import list_adapter_capabilities

        print(
            json.dumps(
                {"capabilities": list_adapter_capabilities()},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "manifest-validate":
        import json
        from pathlib import Path

        from wechat_article_scheduler.core.manifest_loader import validate_manifest_file

        _data, result = validate_manifest_file(Path(args.manifest))
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.ok else 1

    if args.command == "manifest-dry-run":
        import json
        from pathlib import Path

        from wechat_article_scheduler.content_packages.from_manifest import (
            manifest_dry_run_summary,
        )
        from wechat_article_scheduler.core.manifest_loader import load_manifest

        path = Path(args.manifest)
        try:
            summary = manifest_dry_run_summary(load_manifest(path))
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        summary["manifest_path"] = str(path.resolve())
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.command == "projects-dry-run":
        import json
        from pathlib import Path

        from wechat_article_scheduler.config import ROOT
        from wechat_article_scheduler.core.multi_project_dry_run import (
            build_multi_project_dry_run,
        )

        projects_path = Path(args.projects) if args.projects else None
        summary = build_multi_project_dry_run(ROOT, projects_path=projects_path)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("ok") else 1

    if args.command == "local-blog-plan":
        import json

        from wechat_article_scheduler.adapters.local_blog.plans import build_plan

        try:
            plan = build_plan(
                destination=args.destination,
                article_id=args.article_id,
                output_dir=args.output_dir,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "webhook-plan":
        import json

        from wechat_article_scheduler.adapters.webhook.plans import build_plan

        try:
            plan = build_plan(
                channel=args.channel,
                article_id=args.article_id,
                event_type=args.event_type,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "video-package-plan":
        import json

        from wechat_article_scheduler.content_packages.video_presearch import (
            build_video_package_dry_run,
        )

        try:
            plan = build_video_package_dry_run(
                platform=args.platform,
                package_id=args.package_id,
                title=args.title,
                video_path=args.video_path,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "short-video-plan":
        import json

        from wechat_article_scheduler.content_packages.short_video_deferred import (
            build_short_video_deferred_plan,
        )

        try:
            plan = build_short_video_deferred_plan(
                platform=args.platform,
                article_id=args.article_id,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "audio-package-plan":
        import json

        from wechat_article_scheduler.content_packages.audio_presearch import (
            build_audio_package_dry_run,
        )

        try:
            plan = build_audio_package_dry_run(
                platform=args.platform,
                package_id=args.package_id,
                title=args.title,
                audio_path=args.audio_path,
            )
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.command == "wechat-chain-summary":
        import json

        from wechat_article_scheduler.wechat_chain_summary import build_wechat_chain_summary

        db.init_db(config.database_path)
        with db.connect(config.database_path) as conn:
            summary = build_wechat_chain_summary(config, conn)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.command == "mark-waiting-confirmation":
        import json

        from wechat_article_scheduler.review.proof import mark_job_waiting_confirmation

        with db.connect(config.database_path) as conn:
            result = mark_job_waiting_confirmation(conn, args.job_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "submit-proof":
        import json

        from wechat_article_scheduler.review.proof import ProofInput, submit_publish_proof

        with db.connect(config.database_path) as conn:
            result = submit_publish_proof(
                conn,
                args.job_id,
                ProofInput(
                    public_url=args.public_url,
                    screenshot_path=args.screenshot_path,
                    confirmed_by=args.confirmed_by,
                    note=args.note,
                ),
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "export-outbox":
        import json

        from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox

        with db.connect(config.database_path) as conn:
            result = export_article_to_outbox(
                config,
                conn,
                args.article_id,
                platform=args.platform or "generic",
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "reject":
        ok = reject_article(config, args.article_id)
        if not ok:
            print(f"未找到文章 id={args.article_id}")
            return 1
        print(f"已驳回文章 id={args.article_id}")
        return 0

    if args.command == "retry-failed":
        n = retry_failed_jobs(config)
        print(f"已重置 {n} 条 failed 任务为 pending")
        return 0

    if args.command == "update-draft":
        result = update_article_wechat_draft(config, args.article_id)
        for line in result.get("human") or [result.get("error") or "完成"]:
            print(line)
        return 0 if result.get("ok") else 1

    if args.command == "content":
        print_content_library(config, limit=args.limit)
        return 0

    if args.command == "events":
        rows = list_events(config, limit=args.limit)
        for row in rows:
            print(
                f"[{row['id']}] {row['created_at']} {row['event_type']} "
                f"{row['entity_type']}#{row['entity_id']} {row['payload_json'] or ''}"
            )
        return 0

    if args.command == "cover-scan":
        from wechat_article_scheduler.cover_assets import (
            bind_covers_by_stem,
            repair_invalid_cover_paths,
            scan_cover_assets,
        )

        with db.connect(config.database_path) as conn:
            if args.repair:
                rep = repair_invalid_cover_paths(config, conn)
                print("; ".join(rep["human"]))
            if args.bind:
                bound = bind_covers_by_stem(config, conn)
                print("; ".join(bound["human"]))
            report = scan_cover_assets(config, conn)
        for line in report["human"]:
            print(line)
        return 0

    if args.command == "preview-snapshot":
        from wechat_article_scheduler.preview_snapshot import (
            build_article_preview_package,
            save_preview_snapshot,
        )

        with db.connect(config.database_path) as conn:
            row = conn.execute(
                """
                SELECT id, title, summary, body, cover_path
                FROM articles WHERE id = ?
                """,
                (args.article_id,),
            ).fetchone()
        if row is None:
            print(f"文章不存在: id={args.article_id}")
            return 1
        package = build_article_preview_package(config, row, article_id=args.article_id)
        path = save_preview_snapshot(config, package)
        print(f"预览快照已保存: {path}")
        if package.get("render_error"):
            print(f"渲染警告: {package['render_error']}")
        return 0

    if args.command == "serve":
        import uvicorn

        from wechat_article_scheduler.web import create_app

        db.init_db(config.database_path)
        host = args.host or config.web_host
        port = args.port or config.web_port
        app = create_app(config)
        print(f"管理后台: http://{host}:{port}/ （mode={config.wechat_mode}）")
        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
