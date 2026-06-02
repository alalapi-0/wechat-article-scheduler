"""local_blog 多目的地干跑计划入口。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.adapters.local_blog.eval_workflow import (
    DESTINATION_META,
    build_local_blog_dry_run_plan,
)

SUPPORTED_LOCAL_BLOG_DESTINATIONS: dict[str, dict[str, str]] = {
    k: {"label": v["label"], "description": v["summary"][:80]}
    for k, v in DESTINATION_META.items()
}


def list_destinations() -> list[dict[str, str]]:
    return [
        {"id": k, "label": v["label"], "platform": v["platform"]}
        for k, v in DESTINATION_META.items()
    ]


def build_plan(
    *,
    destination: str = "static_site",
    article_id: str | None = None,
    output_dir: str | None = None,
) -> dict[str, Any]:
    return build_local_blog_dry_run_plan(
        destination=destination,
        article_id=article_id,
        output_dir=output_dir,
    )
