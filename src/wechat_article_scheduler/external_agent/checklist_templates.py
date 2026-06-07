"""Checklist template for external browser Agent task packages."""

from __future__ import annotations

CHECKLIST_TEMPLATE = """# 微信公众号草稿检查清单

## 登录与门控

- [ ] 已等待用户扫码登录（不得代填密码）
- [ ] 用户已点击「已登录，继续」

## 内容与字段

- [ ] 草稿标题正确
- [ ] 摘要未超过 120 字
- [ ] 封面显示正常
- [ ] 封面裁剪区域与本地 cover_config 一致
- [ ] 封面是否显示在正文中已核对
- [ ] 横向预览未裁掉主体
- [ ] 正文段落间距正常
- [ ] 正文图片显示正常
- [ ] 作者字段正确
- [ ] 原文链接设置正确
- [ ] 留言开关设置正确
- [ ] 推荐/通知选项已核对（若账号可见）
- [ ] 原创声明已核对（若适用）
- [ ] 合集设置正确

## 定时与发布边界

- [ ] 后台定时时间已设置（对照本地 scheduled_at）
- [ ] 未点击最终定时群发确认（需用户本人操作）
- [ ] 未点击最终发布
- [ ] 已截图或记录 proof
"""


def render_checklist() -> str:
    return CHECKLIST_TEMPLATE
