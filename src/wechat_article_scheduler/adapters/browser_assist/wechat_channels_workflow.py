"""微信视频号 browser_assist 评估干跑（Round 34b / round_097）。"""

from __future__ import annotations

from typing import Any

CHANNELS_GUARDRAILS: list[str] = [
    "不保存视频号/微信登录 cookie",
    "不自动点击「发表」",
    "不上传视频（dry-run 仅清单）",
    "不把视频号能力当作公众号 official_api",
    "人工确认前不得标记为微信公众号已发布",
    "优先 export-outbox --platform wechat_channels",
]

CHANNELS_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "login", "label": "登录视频号助手", "instruction": "用户自行扫码/登录"},
    {"id": "upload", "label": "上传视频", "instruction": "用户自备 video.mp4"},
    {"id": "metadata", "label": "标题描述", "instruction": "channels_title.txt / channels_description.txt"},
    {"id": "cover", "label": "封面", "instruction": "channels_cover_notes.txt"},
    {"id": "mp_link", "label": "公众号关联", "instruction": "可选，见 channels_article_link_note.txt"},
    {"id": "proof", "label": "proof", "instruction": "视频号链接或截图"},
]

CHANNELS_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "导出发布包",
        "actor": "scheduler",
        "detail": "export-outbox --platform wechat_channels",
    },
    {
        "step_id": "open_assistant",
        "title": "打开视频号助手（说明）",
        "actor": "browser_assist",
        "detail": "干跑：channels.weixin.qq.com 类入口 — 不自动打开",
    },
    {
        "step_id": "assist",
        "title": "对照清单",
        "actor": "browser_assist",
        "detail": "channels_publish_checklist.md",
    },
    {
        "step_id": "human_confirm",
        "title": "人工发表",
        "actor": "user",
        "detail": "禁止无人值守",
    },
]

CHANNELS_ASSESSMENT: dict[str, Any] = {
    "risk_level": "high",
    "recommendation": "manual_export_first",
    "summary": "视频号与公众号分离；优先发布包 + 人工上传，browser_assist 仅对照字段。",
    "blockers": ["无视频号官方 API 在本项目", "视频需用户自备"],
    "fallback": "export-outbox --platform wechat_channels",
}


def build_wechat_channels_dry_run_plan(
    *,
    article_id: str | None = None,
    outbox_relative_path: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": "dry_run",
        "platform": "wechat_channels",
        "status": "awaiting_human_confirmation",
        "terminal_policy": "视频号 published ≠ 微信公众号 published",
        "article_id": article_id,
        "outbox_relative_path": outbox_relative_path,
        "guardrails": CHANNELS_GUARDRAILS,
        "human_checkpoints": CHANNELS_CHECKPOINTS,
        "steps": CHANNELS_STEPS,
        "assessment": CHANNELS_ASSESSMENT,
        "target_fields": [
            {"field_id": "title", "label": "标题", "source": "channels_title.txt"},
            {"field_id": "description", "label": "描述", "source": "channels_description.txt"},
            {"field_id": "video", "label": "视频", "source": "video.mp4（用户自备）"},
            {"field_id": "cover", "label": "封面", "source": "cover.*"},
            {"field_id": "mp_relation", "label": "公众号关联", "source": "channels_article_link_note.txt"},
        ],
        "proof_placeholder": {
            "public_url": None,
            "screenshot_path": None,
            "note": "视频号作品链接",
        },
    }
