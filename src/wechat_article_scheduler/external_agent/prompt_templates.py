"""Prompt templates for external browser Agent task packages."""

from __future__ import annotations

from string import Template

PROMPT_TEMPLATE = Template(
    """# 外部浏览器辅助 Agent 操作提示

你是外部浏览器辅助 Agent。
第一步：严格执行 docs/wechat_chrome_session_runbook.md 的阶段 A 到阶段 D。
必须使用 wechat-chrome-session 连接用户现有 Chrome；不得改用 playwright --isolated、普通 chrome-devtools、专用 9222 profile 或项目内登录辅助页。
先完成 list_pages、选择 mp.weixin.qq.com 现有标签页、DOM snapshot 和截图。连接报告不是 PASS 时必须停止。
只允许根据可见页面状态、URL、标题、snapshot 或用户确认判断是否已登录；不得读取 cookie/session/token。
若登录已过期，等待用户在可见 Chrome 页面自行扫码/验证；用户确认前不得继续写操作。
用户确认已登录后，请打开微信公众号后台并进入草稿箱。
请查找标题为《$title》的草稿。
请检查标题、摘要、封面、正文排版是否与任务包一致。
请根据 checklist 设置 API 不能覆盖的后台字段，包括合集、推荐/通知、封面显示和目标定时时间。
完成字段设置后点击“保存草稿”，重新打开同一草稿并核验字段是否持久化。
若目标定时时间不能随草稿保存，明确报告 schedule_persisted=no，并保留目标时间供用户最终发表前回填。
不要绕过登录、扫码、验证码或任何平台安全机制。
不要保存 cookie。
不要点击正式发表、群发或任何会创建真实发布/定时任务的最终确认按钮。
允许点击“保存草稿”；保存后必须停在人类用户最终发表阶段。
正式发表和平台安全验证需要人工确认。

## 任务信息

- job_id: $job_id
- article_id: $article_id
- draft_id: $draft_id
- media_id: $media_id
- planned_time: $scheduled_at
- author: $author
- digest: $digest
- comment_setting: $comment_setting
- collection_name: $collection_name
- content_source_url: $content_source_url

## 后台字段目标（task.json target_field_values）

$target_field_values

## 可执行动作

$required_actions

## 禁止动作

$forbidden_actions

完成检查后，请截图或输出操作报告。
请停在人类用户最终发表阶段，不要提交正式发表、群发或后台定时最终确认。
"""
)


def render_browser_agent_prompt(context: dict[str, object]) -> str:
    """Render the natural-language prompt for Hermes/Cursor/Playwright MCP/etc."""
    values = {key: "" if value is None else str(value) for key, value in context.items()}
    values.setdefault("title", "")
    values.setdefault("job_id", "")
    values.setdefault("article_id", "")
    values.setdefault("draft_id", "")
    values.setdefault("media_id", "")
    values.setdefault("scheduled_at", "")
    values.setdefault("author", "")
    values.setdefault("digest", "")
    values.setdefault("comment_setting", "")
    values.setdefault("collection_name", "")
    values.setdefault("content_source_url", "")
    values.setdefault("required_actions", "")
    values.setdefault("forbidden_actions", "")
    tfv = context.get("target_field_values")
    if isinstance(tfv, dict):
        values["target_field_values"] = "\n".join(f"- {k}: {v}" for k, v in tfv.items())
    else:
        values.setdefault("target_field_values", "")
    return PROMPT_TEMPLATE.safe_substitute(values)
