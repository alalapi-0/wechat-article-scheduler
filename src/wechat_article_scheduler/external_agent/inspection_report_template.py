"""Read-only inspection report template for external Agent task packages."""

from __future__ import annotations

from string import Template

INSPECTION_REPORT_TEMPLATE = Template(
    """# 外部 Agent 只读检查报告

job_id: $job_id
article_title: $title
draft_id: $draft_id
operator:
agent_tool:
checked_at:

## 检查结果

## 已完成的只读检查

## 未完成操作

## 需要人工处理

## 截图路径或链接

## 是否执行公众号后台写操作

否

## 是否点击最终发布

否

## 发布状态声明

本报告只证明完成了只读检查，不能作为发布 proof，也不能将文章标记为已发布。
"""
)


def render_inspection_report(context: dict[str, object]) -> str:
    values = {key: "" if value is None else str(value) for key, value in context.items()}
    values.setdefault("job_id", "")
    values.setdefault("title", "")
    values.setdefault("draft_id", "")
    return INSPECTION_REPORT_TEMPLATE.safe_substitute(values)
