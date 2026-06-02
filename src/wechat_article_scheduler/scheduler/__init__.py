"""调度子包：领域 / 策略 / 运行时分层。"""

from __future__ import annotations

from typing import Any

__all__ = ["run_due_jobs", "scheduler_loop"]


def __getattr__(name: str) -> Any:
    if name == "run_due_jobs":
        from wechat_article_scheduler.scheduler.runtime import run_due_jobs

        return run_due_jobs
    if name == "scheduler_loop":
        from wechat_article_scheduler.scheduler.runtime import scheduler_loop

        return scheduler_loop
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
