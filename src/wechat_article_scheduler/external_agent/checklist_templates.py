"""Checklist template for external browser Agent task packages."""

from __future__ import annotations

CHECKLIST_TEMPLATE = """# 微信公众号草稿检查清单

## 登录与门控

- [ ] 已阅读 docs/wechat_chrome_session_runbook.md
- [ ] 已使用 wechat-chrome-session，而不是 playwright --isolated 或普通 chrome-devtools
- [ ] list_pages 已找到 mp.weixin.qq.com 的现有标签页
- [ ] 已取得同一标签页的 DOM snapshot 和截图
- [ ] 已基于可见页面判断登录状态（不得读取 cookie/session/token）
- [ ] 若登录已过期，已等待用户在可见 Chrome 页面自行扫码（不得代填密码）
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

## 发布前准备与人工发表边界

- [ ] 已确认本地 scheduled_at 仅表示“按时创建草稿”
- [ ] 已填写后台目标定时时间
- [ ] 已点击保存草稿
- [ ] 已重新打开同一草稿核验字段是否持久化
- [ ] 已记录 schedule_persisted=yes/no
- [ ] 未点击正式发表、群发或任何创建真实定时任务的最终确认按钮
- [ ] 未点击最终发布
- [ ] 已截图或记录 proof
"""


def render_checklist() -> str:
    return CHECKLIST_TEMPLATE
