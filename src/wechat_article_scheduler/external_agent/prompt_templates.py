"""Prompt templates for external browser Agent task packages."""

from __future__ import annotations

from string import Template

PROMPT_TEMPLATE = Template(
    """# 外部浏览器辅助 Agent 操作提示

你是外部浏览器辅助 Agent。
只可使用用户明确批准的、可见且已有登录状态的浏览器会话。
不得假装新建或隔离浏览器已经登录；如果没有可用的已登录会话，报告 BLOCKED 并停止。
先确认当前页面属于 mp.weixin.qq.com，并取得可见页面快照或截图。
只允许根据可见页面状态、URL、标题、snapshot 或用户确认判断是否已登录；不得读取 cookie/session/token。
若登录已过期，等待用户在可见 Chrome 页面自行扫码/验证；用户确认前不得继续检查。
用户确认已登录后，请打开微信公众号后台并进入草稿箱。
请查找标题为《$title》的草稿。
请检查标题、摘要、封面、正文排版是否与任务包一致。
请根据 checklist 只读核对合集、推荐/通知、封面显示和后台时间等可见字段，并报告差异。
不得更改任何字段，不得点击“保存草稿”，不得触发任何会写入公众号后台的动作。
不要绕过登录、扫码、验证码或任何平台安全机制。
不要保存 cookie。
不要点击保存草稿、正式发表、群发或任何会创建真实发布/定时任务的确认按钮。
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

## 本地期望值（task.json expected_field_values，仅用于比对）

$expected_field_values

## 可执行动作

$required_actions

## 禁止动作

$forbidden_actions

完成检查后，请截图或输出操作报告。
完成截图与报告后立即停止；不要执行任何后台写操作。
"""
)


def render_browser_agent_prompt(context: dict[str, object]) -> str:
    """Render a tool-neutral prompt for a user-approved external browser tool."""
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
    tfv = context.get("expected_field_values")
    if isinstance(tfv, dict):
        values["expected_field_values"] = "\n".join(f"- {k}: {v}" for k, v in tfv.items())
    else:
        values.setdefault("expected_field_values", "")
    return PROMPT_TEMPLATE.safe_substitute(values)
