"""小红书 browser_assist 评估干跑（Round 33 / round_095）。"""

from __future__ import annotations

from typing import Any

XHS_GUARDRAILS: list[str] = [
    "不保存小红书密码、cookie 或设备指纹",
    "不自动点击「发布」或批量灌水",
    "不上传图片/视频（dry-run 仅清单）",
    "不绕过验证码、实名或社区风控",
    "人工确认前不得标记为已发布",
    "优先 export-outbox --platform xiaohongshu",
]

XHS_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "login", "label": "登录", "instruction": "用户 App/网页自行登录"},
    {"id": "media", "label": "上传素材", "instruction": "对照 xhs_media_placeholder.txt"},
    {"id": "copy", "label": "标题与正文", "instruction": "xhs_title.txt / xhs_note_body.md"},
    {"id": "topics", "label": "话题标签", "instruction": "xhs_tags_hint.md 人工添加"},
    {"id": "publish", "label": "发布确认", "instruction": "用户显式点击发布"},
    {"id": "proof", "label": "proof", "instruction": "笔记链接或截图"},
]

XHS_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "导出发布包",
        "actor": "scheduler",
        "detail": "export-outbox --platform xiaohongshu",
    },
    {
        "step_id": "open_creator",
        "title": "打开发布入口（说明）",
        "actor": "browser_assist",
        "detail": "干跑：创作者中心发布页 — 不自动打开浏览器",
    },
    {
        "step_id": "assist_copy",
        "title": "对照字段",
        "actor": "browser_assist",
        "detail": "对照 xhs_publish_checklist.md",
    },
    {
        "step_id": "human_confirm",
        "title": "人工确认",
        "actor": "user",
        "detail": "高风控：禁止无人值守发布",
    },
]

XHS_ASSESSMENT: dict[str, Any] = {
    "risk_level": "high",
    "recommendation": "deferred",
    "summary": "小红书风控高；仅建议 manual_export 包 + 人工发布，browser_assist 仅作字段对照评估。",
    "blockers": ["反自动化与营销合规", "素材需用户自备"],
    "fallback": "export-outbox --platform xiaohongshu",
}


def build_xiaohongshu_dry_run_plan(
    *,
    article_id: str | None = None,
    outbox_relative_path: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": "dry_run",
        "platform": "xiaohongshu",
        "status": "awaiting_human_confirmation",
        "terminal_policy": "不得自动到达 published",
        "article_id": article_id,
        "outbox_relative_path": outbox_relative_path,
        "guardrails": XHS_GUARDRAILS,
        "human_checkpoints": XHS_CHECKPOINTS,
        "steps": XHS_STEPS,
        "assessment": XHS_ASSESSMENT,
        "target_fields": [
            {"field_id": "title", "label": "标题", "source": "xhs_title.txt"},
            {"field_id": "body", "label": "正文", "source": "xhs_note_body.md"},
            {"field_id": "topics", "label": "话题", "source": "xhs_tags_hint.md"},
            {"field_id": "cover", "label": "封面", "source": "cover.* / xhs_cover_notes.txt"},
            {"field_id": "media", "label": "图集/视频", "source": "xhs_media_placeholder.txt"},
        ],
        "proof_placeholder": {
            "public_url": None,
            "screenshot_path": None,
            "note": "小红书笔记分享链接",
        },
    }
