"""Prompt templates for external browser Agent task packages."""

from __future__ import annotations

from string import Template

PROMPT_TEMPLATE = Template(
    """# 外部浏览器辅助 Agent 操作提示

你是外部浏览器辅助 Agent。
第一步：等待用户在本浏览器窗口扫码登录；用户确认前不得继续写操作。
用户确认已登录后，请打开微信公众号后台并进入草稿箱。
请查找标题为《$title》的草稿。
请检查标题、摘要、封面、正文排版是否与任务包一致。
请根据 checklist 辅助检查或填写允许的字段。
后台定时：可辅助设置定时时间，但不得点击最终定时群发确认。
不要绕过登录、扫码、验证码或任何平台安全机制。
不要保存 cookie。
不要点击最终发布按钮。
本任务需要人工确认；完成检查后必须停在人类用户确认阶段。

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
请停在人类用户确认阶段，不要提交最终发布或最终定时群发确认。
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
