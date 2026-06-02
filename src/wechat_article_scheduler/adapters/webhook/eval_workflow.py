"""Webhook 适配器评估干跑（round_089）。"""

from __future__ import annotations

from typing import Any

WEBHOOK_GUARDRAILS: list[str] = [
    "Webhook 成功仅表示通知送达，不代表目标平台已发布",
    "请求体不得包含 token、cookie 或完整 .env",
    "默认 dry-run 不发起真实 HTTP 请求",
    "URL 仅来自环境变量 WEBHOOK_URL，禁止硬编码到仓库",
    "失败重试需有上限并写审计事件",
    "飞书/Slack/企业微信 payload 需按各平台文档脱敏",
]

CHANNEL_META: dict[str, dict[str, Any]] = {
    "generic": {
        "label": "通用 JSON Webhook",
        "risk_level": "low",
        "recommendation": "recommended",
        "summary": "向自建或 n8n/IFTTT 端点发送文章就绪通知；不替代发布 proof。",
        "sample_fields": ["event", "article_id", "title", "scheduled_at", "preview_url"],
    },
    "feishu": {
        "label": "飞书机器人",
        "risk_level": "low",
        "recommendation": "conditional",
        "summary": "适合运营提醒；需签名校验与群 ID，消息内容应脱敏。",
        "sample_fields": ["msg_type", "content.title", "content.text"],
    },
    "slack": {
        "label": "Slack Incoming Webhook",
        "risk_level": "low",
        "recommendation": "conditional",
        "summary": "适合频道通知；Webhook URL 视为 secret。",
        "sample_fields": ["text", "blocks"],
    },
}

WEBHOOK_STEPS: list[dict[str, str]] = [
    {
        "step_id": "build_payload",
        "title": "组装 payload",
        "actor": "webhook",
        "detail": "干跑输出 JSON 示意，不发送",
    },
    {
        "step_id": "validate_url",
        "title": "校验 URL",
        "actor": "scheduler",
        "detail": "检查 WEBHOOK_URL 已配置且为 https",
    },
    {
        "step_id": "dry_run_send",
        "title": "模拟发送",
        "actor": "webhook",
        "detail": "记录将发送的 method/headers 摘要（无 secret）",
    },
    {
        "step_id": "audit",
        "title": "审计事件",
        "actor": "scheduler",
        "detail": "写入 webhook_attempt 事件；status=simulated",
    },
]


def build_webhook_dry_run_plan(
    *,
    channel: str = "generic",
    article_id: str | None = None,
    event_type: str = "article.ready",
) -> dict[str, Any]:
    """Webhook 评估计划（dry-run，不发起 HTTP）。"""
    key = (channel or "generic").strip().lower()
    meta = CHANNEL_META.get(key)
    if meta is None:
        raise ValueError(
            f"不支持的 webhook channel：{channel}；可选：{', '.join(CHANNEL_META)}"
        )
    payload_preview = {
        "event": event_type,
        "article_id": article_id,
        "channel": key,
        "fields": meta["sample_fields"],
        "note": "dry-run payload preview only",
    }
    return {
        "mode": "dry_run",
        "adapter_type": "webhook",
        "channel": key,
        "status": "simulated",
        "terminal_policy": "webhook_delivered 不等于 published",
        "article_id": article_id,
        "guardrails": WEBHOOK_GUARDRAILS,
        "steps": list(WEBHOOK_STEPS),
        "assessment": {
            "risk_level": meta["risk_level"],
            "recommendation": meta["recommendation"],
            "summary": meta["summary"],
            "blockers": [
                "缺少 WEBHOOK_URL 时只能干跑",
                "不能将通知当作发布 proof",
            ],
            "fallback": "发布 proof 仍走 submit-proof；webhook 仅辅助提醒。",
        },
        "payload_preview": payload_preview,
        "env_hints": ["WEBHOOK_URL", "WEBHOOK_SECRET（可选）"],
    }
