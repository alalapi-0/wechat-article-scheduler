"""知乎 browser_assist 评估干跑计划（Round 25 / round_081）。"""

from __future__ import annotations

from typing import Any

ZHIHU_GUARDRAILS: list[str] = [
    "不保存知乎密码、cookie 或登录态",
    "不绕过验证码、滑块、短信或风控",
    "不自动点击「发布」或「定时发布」",
    "人工确认前不得将本地任务标为已发布",
    "仅辅助打开页面与字段对照，不注入凭据",
    "高风险场景应退回 manual_export 复制发布",
]

ZHIHU_CHECKPOINTS: list[dict[str, str]] = [
    {
        "id": "login",
        "label": "登录知乎",
        "instruction": "用户自行登录 zhihu.com；Agent 不得代填账号密码",
    },
    {
        "id": "editor_open",
        "label": "打开发布编辑器",
        "instruction": "进入写文章/发想法入口（URL 以当前知乎产品为准）",
    },
    {
        "id": "paste_fields",
        "label": "粘贴标题与正文",
        "instruction": "从 outbox 的 zhihu_title.txt / zhihu_body.md 复制，勿声称自动填表已完成",
    },
    {
        "id": "cover_topic",
        "label": "封面与话题",
        "instruction": "上传 cover.*；话题/专栏由用户人工选择",
    },
    {
        "id": "preview_save",
        "label": "预览后保存或发布",
        "instruction": "默认建议仅保存草稿；发布必须用户显式确认",
    },
    {
        "id": "proof_backfill",
        "label": "回填 proof",
        "instruction": "发布后在作品详情提交公开链接或截图路径",
    },
]

ZHIHU_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "本地准备",
        "actor": "scheduler",
        "detail": "先 export-outbox --platform zhihu 生成发布包",
    },
    {
        "step_id": "open_zhihu",
        "title": "打开知乎创作页（仅导航）",
        "actor": "browser_assist",
        "detail": "干跑仅记录目标 URL 示例：https://www.zhihu.com/ — 不自动打开浏览器",
    },
    {
        "step_id": "assist_paste",
        "title": "辅助对照粘贴",
        "actor": "browser_assist",
        "detail": "对照 zhihu_publish_checklist.md 提示用户逐项粘贴",
    },
    {
        "step_id": "screenshot",
        "title": "截图留证",
        "actor": "user",
        "detail": "保存编辑器或发布成功页截图到本地路径",
    },
    {
        "step_id": "human_confirm",
        "title": "人工确认",
        "actor": "user",
        "detail": "用户确认已发布或已保存；禁止无人值守点击发布",
    },
    {
        "step_id": "proof",
        "title": "proof 与状态",
        "actor": "scheduler",
        "detail": "提交 proof 前保持 waiting_confirmation",
    },
]

ZHIHU_ASSESSMENT: dict[str, Any] = {
    "risk_level": "medium_high",
    "recommendation": "conditional",
    "summary": "知乎无官方 API 接入时，仅适合「用户登录 + 本地提示 + manual_export 包」式半自动；不适合无人值守。",
    "blockers": [
        "登录与风控不可绕过",
        "编辑器 DOM 可能频繁变更",
        "自动发布违反平台规则与本仓库安全边界",
    ],
    "fallback": "优先使用 manual_export 知乎包 + 人工复制；browser_assist 仅作清单与检查点。",
}


def build_zhihu_dry_run_plan(
    *,
    article_id: str | None = None,
    outbox_relative_path: str | None = None,
) -> dict[str, Any]:
    """知乎 browser_assist 评估计划（dry-run，不启动浏览器、不联网发布）。"""
    return {
        "mode": "dry_run",
        "platform": "zhihu",
        "status": "awaiting_human_confirmation",
        "terminal_policy": "不得自动到达 published",
        "article_id": article_id,
        "outbox_relative_path": outbox_relative_path,
        "guardrails": ZHIHU_GUARDRAILS,
        "human_checkpoints": ZHIHU_CHECKPOINTS,
        "steps": list(ZHIHU_STEPS),
        "assessment": ZHIHU_ASSESSMENT,
        "target_fields": [
            {
                "field_id": "title",
                "label": "标题",
                "source": "zhihu_title.txt",
            },
            {
                "field_id": "excerpt",
                "label": "导语",
                "source": "zhihu_excerpt.txt",
            },
            {
                "field_id": "body",
                "label": "正文",
                "source": "zhihu_body.md",
            },
            {
                "field_id": "cover",
                "label": "封面",
                "source": "cover.*",
            },
            {
                "field_id": "topic",
                "label": "话题/专栏",
                "source": "人工选择",
            },
        ],
        "proof_placeholder": {
            "screenshot_path": None,
            "public_url": None,
            "confirmed_by": None,
            "confirmed_at": None,
            "note": "知乎帖 URL 或截图路径",
        },
    }
