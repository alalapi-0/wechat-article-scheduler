# 微信公众号 browser_assist 策略

Status: Historical fallback strategy; Round 131 后优先使用外部 Agent 任务包

> 当前项目不内置完整 Browser Agent，也不默认启用浏览器自动化。API 无法覆盖的后台辅助操作优先通过 `docs/external_agent_task_package_design.md` 中的外部 Agent 任务包交给 Hermes、Cursor Agent、Playwright MCP、Browser Use 或用户手动完成。

## 1. 为什么需要 browser_assist

微信公众号官方 API 能覆盖 token、素材、草稿和部分发布能力，但不一定覆盖后台里的所有字段和预览效果。

browser_assist 的必要性来自：

- 有些公众号后台字段可能 API 不支持。
- 有些字段需要后台手动确认。
- 有些预览效果只能在公众号后台看到。
- 作为个人自用工具，可以让本机浏览器辅助操作。

browser_assist 不是绕过平台规则的工具，也不是商业 SaaS 自动发布能力。

## 2. browser_assist 能做什么

允许能力：

- 打开公众号后台。
- 打开草稿箱。
- 辅助定位草稿。
- 辅助填写部分字段。
- 辅助上传或确认封面。
- 辅助截图。
- 辅助记录操作结果。
- 停在人机确认。

## 3. browser_assist 不能做什么

禁止能力：

- 不能绕过登录。
- 不能绕过验证码。
- 不能保存密码。
- 不能保存 cookie。
- 不能规避平台风控。
- 不能默认最终发布。
- 不能批量灌水。
- 不能伪装成官方 API 能力。

## 4. 推荐流程

```text
本地文章
-> API 创建草稿
-> Web 控制台预览
-> 如果 API 字段不足
-> browser_assist 打开公众号后台
-> 自动定位草稿或辅助填写
-> 用户人工确认
-> 用户点击保存或发布
-> 用户回填 proof
-> 本地状态更新
```

## 5. 状态与记录

browser_assist 任务应记录：

- 对应文章 ID。
- 对应微信草稿 media_id 或后台可识别信息。
- 需要人工确认的字段。
- 截图路径或人工备注。
- 用户确认时间。
- 最终状态。

在没有用户确认前，browser_assist 不能把任务标记为已正式发布。

## 6. 操作清单与 dry-run（Round 18）

详细步骤见 [`docs/browser_assist_runbook.md`](browser_assist_runbook.md)。

历史 dry-run 计划入口：`wechat_article_scheduler.adapters.browser_assist.workflow.build_dry_run_plan()`。当前新增任务包出口：`python3 -m wechat_article_scheduler.cli export-agent-task --job-id <job_id>`。

| 阶段 | 执行方 | 说明 |
|------|--------|------|
| 本地预检 | scheduler | API 草稿已创建/更新 |
| 打开后台 | browser_assist + 用户 | 仅导航，用户扫码登录 |
| 核对缺口字段 | browser_assist | 封面裁剪、后台定时、正文封面显示等 |
| 截图 | 用户 | 本地路径，不含凭据 |
| 人工确认 | 用户 | 默认仅保存，不自动发布 |
| proof 回填 | 用户 + 本地 | Round 19 接入最小记录 |

人工确认点（checkpoint）：`login` → `draft_located` → `fields_reviewed` → `save_only` → `proof_backfill`。

## 7. 与其他平台的关系

本文件只讨论微信公众号路线里的 browser_assist。

知乎、豆瓣、小红书、视频号、Bilibili、抖音、快手、网易云音乐等平台的 browser_assist 方案全部进入后期 backlog，当前不开发。
