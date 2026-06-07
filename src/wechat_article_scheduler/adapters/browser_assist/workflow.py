"""browser_assist 干跑计划：操作清单、人工确认点与安全边界（Round 18）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.wechat_field_matrix import field_gaps

GUARDRAILS: list[str] = [
    "不保存密码、cookie 或会话密钥",
    "不绕过验证码、扫码登录或平台风控",
    "不自动点击群发、发布或定时群发确认",
    "人工确认前不得将任务标记为已正式发布",
    "截图与 proof 仅写入用户指定本地路径，不入库敏感凭据",
]

HUMAN_CHECKPOINTS: list[dict[str, str]] = [
    {
        "id": "login_gate",
        "label": "手动登录门控",
        "instruction": "打开 mp.weixin.qq.com 或 wechat-chrome-session；等待用户扫码后点击「已登录，继续」",
    },
    {
        "id": "login",
        "label": "登录公众号后台",
        "instruction": "用户自行扫码/登录；Agent 不得代填账号密码",
    },
    {
        "id": "draft_located",
        "label": "定位草稿",
        "instruction": "根据 media_id 或标题在草稿箱找到对应条目",
    },
    {
        "id": "fields_reviewed",
        "label": "核对 API 缺口字段",
        "instruction": "封面裁剪、后台定时、正文封面显示等需在后台目视确认",
    },
    {
        "id": "schedule_setup",
        "label": "设置后台定时（非最终确认）",
        "instruction": "Agent 可辅助填写定时时间；不得点击最终定时群发确认",
    },
    {
        "id": "final_schedule_confirm",
        "label": "后台最终定时确认",
        "instruction": "必须由用户本人在公众号后台点击；Agent 仅等待 attestation",
    },
    {
        "id": "save_only",
        "label": "仅保存草稿（可选）",
        "instruction": "默认停在保存；发布需用户显式点击且二次确认",
    },
    {
        "id": "proof_backfill",
        "label": "回填 proof",
        "instruction": "截图路径、公开链接、确认人与时间写入本地记录（Round 19）",
    },
]

WORKFLOW_STEPS: list[dict[str, str]] = [
    {
        "step_id": "preflight",
        "title": "本地预检",
        "actor": "scheduler",
        "detail": "确认 API 草稿已创建/更新；记录 article_id 与 media_id",
    },
    {
        "step_id": "login_gate",
        "title": "等待用户扫码登录",
        "actor": "user",
        "detail": "打开 mp.weixin.qq.com 或连接 wechat-chrome-session；阻塞至用户确认已登录",
    },
    {
        "step_id": "open_mp",
        "title": "打开公众号后台",
        "actor": "browser_assist",
        "detail": "在已登录会话中打开草稿箱（仅导航，不注入凭据）",
    },
    {
        "step_id": "assist_fields",
        "title": "辅助核对缺口字段",
        "actor": "browser_assist",
        "detail": "对照 target_fields 提示用户修改封面裁剪、定时或显示选项",
    },
    {
        "step_id": "screenshot",
        "title": "截图留证",
        "actor": "user",
        "detail": "保存后台预览或草稿编辑页截图到 storage/ 或用户目录",
    },
    {
        "step_id": "human_confirm",
        "title": "人工确认",
        "actor": "user",
        "detail": "用户确认保存结果；禁止无人值守最终发布",
    },
    {
        "step_id": "state_sync",
        "title": "本地状态同步",
        "actor": "scheduler",
        "detail": "有 proof 后更新任务状态；无 proof 保持 waiting_confirmation",
    },
]

BROWSER_ASSIST_FIELD_IDS = frozenset(
    {"cover_crop", "wechat_backend_schedule", "show_cover_pic"},
)


def browser_assist_field_rows() -> list[dict[str, Any]]:
    """能力矩阵中建议走 browser_assist 的字段行。"""
    out: list[dict[str, Any]] = []
    for row in field_gaps():
        fid = row["field_id"]
        handling = row.get("handling", "")
        if fid in BROWSER_ASSIST_FIELD_IDS or "browser_assist" in handling:
            out.append(dict(row))
    return out


def build_dry_run_plan(
    *,
    article_id: str | None = None,
    media_id: str | None = None,
) -> dict[str, Any]:
    """生成可执行的 dry-run 计划（不启动浏览器、不联网）。"""
    targets = browser_assist_field_rows()
    field_ids = [r["field_id"] for r in targets]
    steps = list(WORKFLOW_STEPS)
    if not field_ids:
        steps.append(
            {
                "step_id": "noop",
                "title": "无 browser_assist 缺口",
                "actor": "system",
                "detail": "当前字段矩阵无待人工字段；仅保留 guardrails 供查阅",
            }
        )
    return {
        "mode": "dry_run",
        "platform": "wechat_official",
        "status": "awaiting_human_confirmation",
        "session_status_hint": "awaiting_browser_login",
        "manual_trigger_only": True,
        "login_gate_required": True,
        "terminal_policy": "不得自动到达 published",
        "article_id": article_id,
        "media_id": media_id,
        "guardrails": GUARDRAILS,
        "human_checkpoints": HUMAN_CHECKPOINTS,
        "steps": steps,
        "target_fields": targets,
        "target_field_ids": field_ids,
        "proof_placeholder": {
            "screenshot_path": None,
            "public_url": None,
            "confirmed_by": None,
            "confirmed_at": None,
            "note": "在作品详情或 POST /api/publish-jobs/{id}/proof 回填",
        },
    }
