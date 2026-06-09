# 外部 Agent 集成指南

Status: Current operational guide

## 通用执行流程

1. 本项目生成任务包。
2. 用户打开外部 Agent。
3. 用户把 `browser_agent_prompt.md` 发给外部 Agent。
4. 外部 Agent 打开微信公众号后台。
5. 外部 Agent 定位草稿。
6. 外部 Agent 根据 `checklist.md` 检查字段。
7. 外部 Agent 记录 API 不能覆盖的后台人工事项。
8. 外部 Agent 截图或生成报告。
9. 外部 Agent 停止，不点击最终发布。
10. 用户人工确认。
11. 用户将 proof 填回本项目；proof 可以证明草稿已核对或用户已人工处理后台步骤。
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

将 `browser_agent_prompt.md` 的完整内容交给 Hermes，并把同目录的 `task.json`、`checklist.md`、`article_preview.html` 作为上下文。Hermes 必须停在人类确认阶段，不能点击发布、群发或后台定时确认。

## Cursor Agent + 已登录 Chrome

在 Cursor 中打开任务包目录，把 `browser_agent_prompt.md` 作为任务说明。若要复用已登录的 Chrome：

1. 在 Chrome 144+ 打开 `chrome://inspect/#remote-debugging` 并开启远程调试。
2. 在 Cursor 的 Tools & MCP 确认 `wechat-chrome-session` 已加载。
3. 用户批准 Chrome 的调试连接弹窗。
4. 先让 Agent 列出标签页、截图并核对公众号账号，不做写操作。
5. 先用 1 篇测试草稿验证定位、保存、截图和 proof。
6. 批量前由项目生成 manifest，用户确认整批后再执行。

`wechat-chrome-session` 与 Codex 内置 Chrome 工具是两个独立的工具边界。Codex 对特定站点的限制不能通过仓库代码解除，但 Cursor 可以在其 MCP 和用户授权允许时使用这条通道。

Cursor Agent 只允许执行任务包和已确认 manifest 中的检查动作。发布、群发和确认定时发布属于真实外部副作用，必须由用户本人在公众号后台完成。

## Playwright MCP 使用方式占位

普通 Playwright MCP 使用隔离会话，适合本地工作台 E2E，不适合直接复用日常 Chrome 登录态。不得保存或导出登录态，不得绕过扫码、验证码或平台风控。

## Browser Use 使用方式占位

把 `browser_agent_prompt.md` 作为 Browser Use 任务说明，并限制 Browser Use 只做定位、核对、截图和报告。最终提交、群发或定时确认必须由用户本人完成。
