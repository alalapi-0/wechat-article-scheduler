"""豆瓣 browser_assist 评估干跑计划（Round 27 / round_083）。"""

from __future__ import annotations

from typing import Any

DOUBAN_GUARDRAILS: list[str] = [
    "不保存豆瓣密码、cookie 或登录态",
    "不绕过验证码、风控或实名限制",
    "不自动点击「发布」或「提交审核」",
    "人工确认前不得将本地任务标为已发布",
    "仅辅助对照 outbox 字段，不注入凭据",
    "编辑器结构变更频繁，应优先 manual_export 复制",
]

DOUBAN_CHECKPOINTS: list[dict[str, str]] = [
    {
        "id": "login",
        "label": "登录豆瓣",
        "instruction": "用户自行登录 douban.com；Agent 不得代填账号密码",
    },
    {
        "id": "editor_open",
        "label": "进入写日记/发笔记",
        "instruction": "按当前豆瓣产品入口人工进入编辑器",
    },
    {
        "id": "paste_fields",
        "label": "粘贴标题与正文",
        "instruction": "从 douban_title.txt / douban_body.md 复制",
    },
    {
        "id": "tags_channel",
        "label": "标签与频道",
        "instruction": "参考 douban_tags_hint.md 人工选择，不可自动打标",
    },
    {
        "id": "cover",
        "label": "封面/配图",
        "instruction": "上传 cover.* 或单独配图",
    },
    {
        "id": "preview_publish",
        "label": "预览后发布",
        "instruction": "用户显式确认后才可发布；禁止无人值守",
    },
    {
        "id": "proof_backfill",
        "label": "回填 proof",
        "instruction": "笔记链接或截图路径写入作品详情 proof",
    },
]

DOUBAN_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "本地准备",
        "actor": "scheduler",
        "detail": "先 export-outbox --platform douban 生成发布包",
    },
    {
        "step_id": "open_douban",
        "title": "打开豆瓣（仅导航说明）",
        "actor": "browser_assist",
        "detail": "干跑记录目标站点示例：https://www.douban.com/ — 不自动打开浏览器",
    },
    {
        "step_id": "assist_paste",
        "title": "辅助对照粘贴",
        "actor": "browser_assist",
        "detail": "对照 douban_publish.md 与 checklist 提示用户操作",
    },
    {
        "step_id": "screenshot",
        "title": "截图留证",
        "actor": "user",
        "detail": "保存发布成功页或笔记页截图",
    },
    {
        "step_id": "human_confirm",
        "title": "人工确认",
        "actor": "user",
        "detail": "用户确认已发布；禁止 Agent 代点发布按钮",
    },
    {
        "step_id": "proof",
        "title": "proof 与状态",
        "actor": "scheduler",
        "detail": "无 proof 前保持 waiting_confirmation",
    },
]

DOUBAN_ASSESSMENT: dict[str, Any] = {
    "risk_level": "medium",
    "recommendation": "conditional",
    "summary": "豆瓣无官方 API 时，适合「manual_export 包 + 人工登录 + 清单辅助」；不适合无人值守自动发布。",
    "blockers": [
        "登录与社区规范限制",
        "标签/频道需人工判断",
        "自动发布违反安全边界",
    ],
    "fallback": "优先 douban 发布包复制；browser_assist 仅提供步骤与检查点。",
}


def build_douban_dry_run_plan(
    *,
    article_id: str | None = None,
    outbox_relative_path: str | None = None,
) -> dict[str, Any]:
    """豆瓣 browser_assist 评估计划（dry-run，不联网发布）。"""
    return {
        "mode": "dry_run",
        "platform": "douban",
        "status": "awaiting_human_confirmation",
        "terminal_policy": "不得自动到达 published",
        "article_id": article_id,
        "outbox_relative_path": outbox_relative_path,
        "guardrails": DOUBAN_GUARDRAILS,
        "human_checkpoints": DOUBAN_CHECKPOINTS,
        "steps": list(DOUBAN_STEPS),
        "assessment": DOUBAN_ASSESSMENT,
        "target_fields": [
            {"field_id": "title", "label": "标题", "source": "douban_title.txt"},
            {"field_id": "intro", "label": "简介", "source": "douban_intro.txt"},
            {"field_id": "body", "label": "正文", "source": "douban_body.md"},
            {"field_id": "tags", "label": "标签", "source": "douban_tags_hint.md"},
            {"field_id": "cover", "label": "封面", "source": "cover.*"},
        ],
        "proof_placeholder": {
            "screenshot_path": None,
            "public_url": None,
            "confirmed_by": None,
            "confirmed_at": None,
            "note": "豆瓣笔记/日记 URL",
        },
    }
