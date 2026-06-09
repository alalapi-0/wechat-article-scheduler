# 外部 Agent 浏览器说明

**仓库**：wechat-article-scheduler  
**基线日期**：2026-06-07

本文说明本仓库 **内置能力** 与 **外部 Browser Agent** 的分工，以及当前 MCP 能力与外部 Agent 的关系。

---

## 1. 本仓库项目本体负责

| 职责 | 说明 |
|------|------|
| 文章扫描 | `scan`、去重、入库 |
| 渲染 | Markdown / HTML → 微信公众号正文 |
| 草稿创建 | API 模式创建/更新草稿（`WECHAT_MODE=mock` 默认） |
| 任务排期 | scheduler、队列、失败重试 |
| 任务包导出 | `outbox/wechat_agent_tasks/job-xxxxxx/` |
| proof 记录 | 人工确认后的核对记录回填 |

本仓库 **不内置** 完整 Browser Agent，不集成 Hermes SDK、Browser Use SDK 作为运行时依赖。

---

## 2. 外部 Agent 负责

外部 Agent 可以是 Hermes、Cursor Agent、Playwright MCP、Browser Use 或用户本人，接收任务包后负责：

| 职责 | 边界 |
|------|------|
| 打开已登录微信公众号后台 | 须使用正确浏览器上下文（见下文） |
| 定位草稿 | 按 `task.json` / `browser_agent_prompt.md` |
| 检查草稿字段 | 按 `checklist.md` |
| 辅助填写后台字段 | API 不能覆盖的字段 |
| 截图 / 生成报告 | 供用户核对 |
| **停在人机确认** | **不点击最终发布** |

### 任务包结构（默认）

```text
outbox/wechat_agent_tasks/job-xxxxxx/
├── browser_agent_prompt.md
├── task.json
├── checklist.md
├── article_preview.html
└── ...
```

导出命令：

```bash
python3 -m wechat_article_scheduler.cli export-agent-task --job-id <id>
```

详见 [`docs/external_agent_integration_guide.md`](../external_agent_integration_guide.md)。

---

## 3. 当前 MCP 能力与外部 Agent 的关系

### 本地 Web UI 测试

| MCP | 角色 |
|-----|------|
| chrome-devtools | 本地 `http://127.0.0.1:8080/` 调试 |
| playwright (`--isolated`) | 本地 Web UI E2E |

两者当前均为 **隔离浏览器**，适合验证本仓库 Web 工作台，**不等于**已登录公众号后台。

### 微信公众号后台操作

| 方式 | 适用 |
|------|------|
| **wechat-chrome-session** | Cursor 内复用用户已批准的本机 Chrome |
| 外部 Hermes / Browser Use | 用户在其环境配置已登录浏览器 |
| Playwright MCP（非 isolated + 持久 profile） | 须用户明确配置，profile 不入库 |

**关键**：playwright / chrome-devtools 的 isolated 实例 **不能** 代替「已登录公众号后台」上下文。外部 Agent 若误用 isolated browser，会与 Cursor 内犯同样错误。

### Cursor Agent 作为外部 Agent

- 可把 `browser_agent_prompt.md` 作为任务说明
- 操作公众号后台时 **必须** 使用 `wechat-chrome-session`，不用 isolated playwright
- 与 Codex 内置 Chrome 工具是 **独立边界**；以本仓库 MCP 策略为准

### 关系示意

```text
┌─────────────────────────────────────┐
│  wechat-article-scheduler（本体）    │
│  scan / plan / draft API / 任务包    │
└──────────────┬──────────────────────┘
               │ export-agent-task
               ▼
┌─────────────────────────────────────┐
│  外部 Browser Agent                  │
│  Hermes / Cursor / Playwright MCP   │
│  打开已登录后台 → 核对 → 截图 → 停止  │
└──────────────┬──────────────────────┘
               │ proof 回填
               ▼
┌─────────────────────────────────────┐
│  用户人工确认 → 可选：本人后台发布    │
└─────────────────────────────────────┘
```

---

## 4. 安全边界

| 规则 | 说明 |
|------|------|
| 不把 cookie 放进任务包 | 任务包只含 prompt、清单、预览等 |
| 不把 cookie 发给 LLM | 模型上下文不得含 session 明文 |
| 不默认点击最终发布 | 外部 Agent 停在人类确认 |
| 不绕过验证码 | 出现验证码即停止 |
| 不绕过扫码 | 登录过期须用户扫码 |
| 不隐藏操作 | 截图、报告须可追溯 |
| 不提交 browser profile | profile 目录仓库外或 `.gitignore` |

与 [`docs/external_agent_safety_policy.md`](../external_agent_safety_policy.md) 一致。

---

## 5. Agent 选型参考

| 场景 | 推荐 |
|------|------|
| 本地 Web 工作台开发/验收 | Cursor + chrome-devtools / playwright（isolated） |
| Cursor 内操作已登录公众号 | Cursor + wechat-chrome-session |
| 用户偏好独立 Hermes 会话 | 任务包 + Hermes + 用户自备已登录浏览器 |
| 批量草稿核对 | 先单篇 proof，再 manifest 批量（须用户确认） |

---

## 相关文档

- [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md)
- [`browser_context_guide.md`](browser_context_guide.md)
- [`../external_agent_integration_guide.md`](../external_agent_integration_guide.md)
- [`../external_agent_safety_policy.md`](../external_agent_safety_policy.md)
- [`../external_agent_task_package_design.md`](../external_agent_task_package_design.md)
