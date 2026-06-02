"""Bilibili 上传页 browser_assist 评估干跑（Round 31 / round_093）。"""

from __future__ import annotations

from typing import Any

BILIBILI_GUARDRAILS: list[str] = [
    "不保存 B 站密码、cookie 或登录态",
    "不自动点击「投稿」或「立即发布」",
    "不上传视频文件（dry-run 仅步骤清单）",
    "不绕过验证码、实名或版权审核",
    "人工确认前不得标记为已发布",
    "优先使用 manual_export bilibili 发布包对照字段",
]

BILIBILI_CHECKPOINTS: list[dict[str, str]] = [
    {"id": "login", "label": "登录创作中心", "instruction": "用户自行登录；Agent 不代填"},
    {"id": "select_video", "label": "选择视频", "instruction": "从 outbox 目录选择用户自备 video.mp4"},
    {"id": "metadata", "label": "标题与简介", "instruction": "对照 bilibili_title.txt / bilibili_description.txt"},
    {"id": "cover_tags", "label": "封面与标签", "instruction": "对照 cover 与 bilibili_tags_hint.md"},
    {"id": "submit_review", "label": "提交审核", "instruction": "用户显式确认后才可提交"},
    {"id": "proof", "label": "回填 proof", "instruction": "BV 号链接或截图"},
]

BILIBILI_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "导出发布包",
        "actor": "scheduler",
        "detail": "export-outbox --platform bilibili",
    },
    {
        "step_id": "open_creator",
        "title": "打开创作中心（说明）",
        "actor": "browser_assist",
        "detail": "干跑示例：https://member.bilibili.com/platform/upload/video — 不自动打开",
    },
    {
        "step_id": "assist_fields",
        "title": "对照字段",
        "actor": "browser_assist",
        "detail": "对照 bilibili_upload_checklist.md",
    },
    {
        "step_id": "human_confirm",
        "title": "人工确认",
        "actor": "user",
        "detail": "禁止无人值守投稿",
    },
]

BILIBILI_ASSESSMENT: dict[str, Any] = {
    "risk_level": "high",
    "recommendation": "manual_export_first",
    "summary": "视频上传风控高；优先 bilibili 发布包 + 人工上传，browser_assist 仅辅助对照。",
    "blockers": ["视频二进制无法从文章表自动生成", "审核与版权需人工处理"],
    "fallback": "export-outbox --platform bilibili",
}


def build_bilibili_dry_run_plan(
    *,
    article_id: str | None = None,
    outbox_relative_path: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": "dry_run",
        "platform": "bilibili",
        "status": "awaiting_human_confirmation",
        "terminal_policy": "不得自动到达 published",
        "article_id": article_id,
        "outbox_relative_path": outbox_relative_path,
        "guardrails": BILIBILI_GUARDRAILS,
        "human_checkpoints": BILIBILI_CHECKPOINTS,
        "steps": BILIBILI_STEPS,
        "assessment": BILIBILI_ASSESSMENT,
        "target_fields": [
            {"field_id": "title", "label": "标题", "source": "bilibili_title.txt"},
            {"field_id": "description", "label": "简介", "source": "bilibili_description.txt"},
            {"field_id": "video", "label": "视频", "source": "video.mp4（用户自备）"},
            {"field_id": "cover", "label": "封面", "source": "cover.*"},
            {"field_id": "tags", "label": "标签/分区", "source": "bilibili_tags_hint.md"},
        ],
        "proof_placeholder": {
            "public_url": None,
            "screenshot_path": None,
            "note": "BV 号或稿件链接",
        },
    }
