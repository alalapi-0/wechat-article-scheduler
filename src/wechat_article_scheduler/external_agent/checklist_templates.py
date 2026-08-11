"""Checklist template for external browser Agent task packages."""

from __future__ import annotations

CHECKLIST_TEMPLATE = """# 微信公众号草稿检查清单

## 登录与门控

- [ ] 用户已批准使用当前可见的既有登录会话
- [ ] 未假装新建或隔离浏览器已经登录
- [ ] 已确认当前页面属于 mp.weixin.qq.com
- [ ] 已取得当前页面的可见快照或截图
- [ ] 若无可用的已登录会话，已报告 BLOCKED 并停止
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

## 只读核对边界

- [ ] 已确认本地 scheduled_at 仅表示“按时创建草稿”
- [ ] 只读比对了后台可见字段与本地期望值
- [ ] 未修改标题、正文、封面、合集、留言或任何其他字段
- [ ] 未点击保存草稿
- [ ] 未点击正式发表、群发或任何创建真实定时任务的最终确认按钮
- [ ] 未点击最终发布
- [ ] 已填写 inspection_report.md
"""


def render_checklist() -> str:
    return CHECKLIST_TEMPLATE
