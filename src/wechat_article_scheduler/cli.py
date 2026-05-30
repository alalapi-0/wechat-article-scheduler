"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from wechat_article_scheduler import db
from wechat_article_scheduler.config import load_config
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.events_cli import list_events
from wechat_article_scheduler.scheduler import run_due_jobs, scheduler_loop
from wechat_article_scheduler.workflow import reject_article, retry_failed_jobs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="微信公众号文章本地调度器（默认 mock）")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="初始化 SQLite 表结构")
    sub.add_parser("scan", help="扫描 articles/inbox 并导入")
    sub.add_parser("plan", help="为已导入文章生成发布计划")
    sub.add_parser("run-once", help="执行所有已到期的发布任务")
    sub.add_parser("scheduler", help="后台轮询调度（阻塞）")

    reject_p = sub.add_parser("reject", help="驳回文章 (Round 1)")
    reject_p.add_argument("--article-id", type=int, required=True)

    sub.add_parser("retry-failed", help="重试失败的发布任务 (Round 1)")

    events_p = sub.add_parser("events", help="列出最近审计事件 (Round 2)")
    events_p.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    config = load_config()

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

    if args.command == "scheduler":
        try:
            scheduler_loop(config)
        except KeyboardInterrupt:
            print("\n调度器已停止")
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

    if args.command == "events":
        rows = list_events(config, limit=args.limit)
        for row in rows:
            print(
                f"[{row['id']}] {row['created_at']} {row['event_type']} "
                f"{row['entity_type']}#{row['entity_id']} {row['payload_json'] or ''}"
            )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
