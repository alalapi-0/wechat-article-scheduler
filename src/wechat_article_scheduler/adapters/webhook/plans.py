"""Webhook 干跑计划入口。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.adapters.webhook.eval_workflow import (
    CHANNEL_META,
    build_webhook_dry_run_plan,
)

SUPPORTED_WEBHOOK_CHANNELS: dict[str, dict[str, str]] = {
    k: {"label": v["label"], "description": v["summary"][:72]}
    for k, v in CHANNEL_META.items()
}


def list_channels() -> list[dict[str, str]]:
    return [{"id": k, "label": v["label"]} for k, v in CHANNEL_META.items()]


def build_plan(
    *,
    channel: str = "generic",
    article_id: str | None = None,
    event_type: str = "article.ready",
) -> dict[str, Any]:
    return build_webhook_dry_run_plan(
        channel=channel,
        article_id=article_id,
        event_type=event_type,
    )
