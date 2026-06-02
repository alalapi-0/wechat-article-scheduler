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
