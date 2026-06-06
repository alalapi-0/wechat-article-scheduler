"""Proof template for external browser Agent task packages."""

from __future__ import annotations

from string import Template

PROOF_TEMPLATE = Template(
    """# 外部 Agent 操作证明

job_id: $job_id
article_title: $title
draft_id: $draft_id
operator:
agent_tool:
checked_at:

## 检查结果

## 已完成操作

## 未完成操作

## 需要人工处理

## 截图路径或链接

## 是否点击最终发布

否
"""
)


def render_proof_template(context: dict[str, object]) -> str:
    values = {key: "" if value is None else str(value) for key, value in context.items()}
    values.setdefault("job_id", "")
    values.setdefault("title", "")
    values.setdefault("draft_id", "")
    return PROOF_TEMPLATE.safe_substitute(values)
