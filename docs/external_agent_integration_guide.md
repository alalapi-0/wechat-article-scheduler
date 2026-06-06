# 外部 Agent 集成指南

Status: Current operational guide

## 通用执行流程

1. 本项目生成任务包。
2. 用户打开外部 Agent。
3. 用户把 `browser_agent_prompt.md` 发给外部 Agent。
4. 外部 Agent 打开微信公众号后台。
5. 外部 Agent 定位草稿。
6. 外部 Agent 根据 `checklist.md` 检查字段。
7. 外部 Agent 辅助填写允许的非最终设置。
8. 外部 Agent 截图或生成报告。
9. 外部 Agent 停止，不点击最终发布。
10. 用户人工确认。
11. 用户将 proof 填回本项目。
12. 本项目更新任务状态或记录 proof。

## 生成任务包

指定单个发布任务：

```bash
python3 -m wechat_article_scheduler.cli export-agent-task --job-id 1
```

按状态批量导出：

```bash
python3 -m wechat_article_scheduler.cli export-agent-tasks --status draft_created
```

默认导出目录：

```text
outbox/wechat_agent_tasks/
```

## Hermes 使用方式占位

将 `browser_agent_prompt.md` 的完整内容交给 Hermes，并把同目录的 `task.json`、`checklist.md`、`article_preview.html` 作为上下文。Hermes 必须停在人类确认阶段，不能点击最终发布。

## Cursor Agent 使用方式占位

在 Cursor 中打开任务包目录，把 `browser_agent_prompt.md` 作为任务说明。若使用浏览器 MCP 或 Chrome 调试能力，只允许执行任务包列出的允许动作。

## Playwright MCP 使用方式占位

通过 Playwright MCP 打开微信公众号后台并执行可见浏览器检查。不得保存登录态，不得绕过扫码、验证码或平台风控，不得点击最终发布。

## Browser Use 使用方式占位

把 `browser_agent_prompt.md` 作为 Browser Use 任务说明，并限制 Browser Use 只做定位、核对、填写非最终字段、截图和报告。最终提交必须由用户确认。

