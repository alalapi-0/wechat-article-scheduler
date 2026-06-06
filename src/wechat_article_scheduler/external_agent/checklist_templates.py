"""Checklist template for external browser Agent task packages."""

from __future__ import annotations

CHECKLIST_TEMPLATE = """# 微信公众号草稿检查清单

- [ ] 草稿标题正确
- [ ] 摘要未超过 120 字
- [ ] 封面显示正常
- [ ] 横向预览未裁掉主体
- [ ] 正文段落间距正常
- [ ] 正文图片显示正常
- [ ] 作者字段正确
- [ ] 原文链接设置正确
- [ ] 留言开关设置正确
- [ ] 合集设置正确
- [ ] 定时发布设置正确，或确认需要手动设置
- [ ] 未点击最终发布
- [ ] 已截图或记录 proof
"""


def render_checklist() -> str:
    return CHECKLIST_TEMPLATE
