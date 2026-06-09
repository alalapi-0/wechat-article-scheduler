# Cursor MCP 稳定运行 Runbook

**仓库**：wechat-article-scheduler  
**基线日期**：2026-06-07  
**适用线程**：普通前台 Agent（非 Multitask / 非后台子 Agent）  
**权威配置**：`.cursor/mcp.json`

---

## 1. Runbook 目标

本 Runbook 用于确认 **Cursor 当前对话线程** 是否已经暴露本仓库所需 MCP 工具，并在任务开始前建立可重复的 readiness 基线。

**适用于**：

- 本仓库 `wechat-article-scheduler`
- 普通前台 Agent 线程
- 功能测试、文档治理、Web UI 验证、GitHub 辅助、文件系统读写
- Cursor Agent、Codex Agent、推进轮 Agent 的任务启动前检查

**不用于**：

- 绕过微信公众号登录、验证码或风控
- 代替用户点击最终发布
- 导出或传播 cookie、token、API Key

> **关键区分**：配置检查 PASS ≠ 当前线程 tools 已暴露。两层检查都必须做。

---

## 2. 快速检查命令

在仓库根目录执行：

```bash
node scripts/check_mcp_config.js
npm run check:stitch
```

| 命令 | 检查内容 |
|------|----------|
| `node scripts/check_mcp_config.js` | `.cursor/mcp.json` 声明是否完整；7 个 server 是否均已配置 |
| `npm run check:stitch` | Stitch stdio proxy、设计目录、`STITCH_API_KEY` 占位是否可用 |

**说明**：

- 上述命令只验证 **配置层**（2026-06-07 基线：两者均 PASS）
- 命令通过 **不等于** 当前 Agent 线程已加载 MCP tools
- 配置通过后，必须在 **当前对话** 中对每个核心 MCP 做最小探测
- CLI 辅助：`npm run check:cursor-mcp`（不代表当前线程已暴露工具）

---

## 3. 当前线程最小探测流程

对每个 MCP 在当前对话中调用一次代表工具，记录结果。

### chrome-devtools

```text
调用：list_pages
预期：返回至少一个页面，例如 about:blank
```

**2026-06-07 基线**：成功，返回 1 个 `about:blank` 页面。

### playwright

```text
调用：browser_tabs，action=list
预期：返回至少一个 tab，例如 about:blank
```

**2026-06-07 基线**：成功，返回 1 个 `about:blank` tab。

### context7

```text
调用：resolve-library-id，示例查询 FastAPI
预期：返回库 ID
```

**2026-06-07 基线**：成功解析 FastAPI 库 ID。

### filesystem

```text
调用：list_allowed_directories
预期：返回 /Users/alalapi/PycharmProjects/wechat-article-scheduler
```

**2026-06-07 基线**：成功，允许目录为仓库根路径。

### github

```text
调用：search_repositories，搜索 alalapi-0/wechat-article-scheduler
预期：能找到仓库
```

**2026-06-07 基线**：成功搜索到 `alalapi-0/wechat-article-scheduler`。

### stitch

```text
调用：list_projects
预期：返回私有项目列表
```

**2026-06-07 基线**：成功，返回 3 个私有项目。

### wechat-chrome-session（公众号后台专用，另测）

本次 6 项基线探测 **未包含** `wechat-chrome-session`。涉及已登录公众号后台时，必须单独确认该 server 在当前线程可用，并调用 `list_pages` 验证是否能看到 `mp.weixin.qq.com` 标签页。详见 [`browser_context_guide.md`](browser_context_guide.md) 与 [`docs/wechat_chrome_session_runbook.md`](../wechat_chrome_session_runbook.md)。

### 线程探测失败时

输出 `BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY`，停止依赖该 MCP 的任务，按 [`mcp_troubleshooting.md`](mcp_troubleshooting.md) 恢复。

---

## 4. MCP Server 总览表

| MCP Server | 线程 server 名 | 当前状态 | tools 数 | prompts | resources | 最小探测 | 主要用途 | 注意事项 |
|------------|----------------|----------|----------|---------|-----------|----------|----------|----------|
| chrome-devtools | `project-0-wechat-article-scheduler-chrome-devtools` | 可用 | 29 | 无 | 无 | `list_pages` → `about:blank` | 本地页面调试、console、network、截图 | **隔离浏览器**；不适合复用已登录公众号后台 |
| playwright | `project-0-wechat-article-scheduler-playwright` | 可用 | 23 | 无 | 无 | `browser_tabs` list → `about:blank` | 本地 Web UI E2E、表单、跳转 | **`--isolated`**；不适合复用用户 Chrome 登录态 |
| context7 | `project-0-wechat-article-scheduler-context7` | 可用 | 2 | 无 | 无 | `resolve-library-id`（FastAPI） | 第三方库文档查询 | 不用于业务数据读取 |
| filesystem | `project-0-wechat-article-scheduler-filesystem` | 可用 | 14 | 无 | 无 | `list_allowed_directories` | 仓库内读写、搜索 | 仅允许目录内；不写密钥/cookie/profile |
| github | `project-0-wechat-article-scheduler-github` | 可用 | 26 | 无 | 无 | `search_repositories` | 查仓库、issue、PR | token 已生效；默认不主动 push/建 PR |
| stitch | `project-0-wechat-article-scheduler-stitch` | 可用 | 15 | 无 | 无 | `list_projects` | UI 原型、screen 生成 | key 已生效；默认不在普通推进轮使用 |
| wechat-chrome-session | （配置已声明，线程探测另做） | 配置层 PASS | — | — | — | `list_pages` → `mp.weixin.qq.com` | 复用用户已登录 Chrome 操作公众号后台 | **唯一**适合已登录后台的 Workspace MCP |

**补充**：

- 配置层共声明 **7** 个 server（含 `wechat-chrome-session`）
- 本线程另有 **cursor-ide-browser**（Cursor 内置），不在上述 Workspace MCP 基线范围内
- 2026-06-07 基线：6 项核心 MCP 探测均成功；无需重启、无需额外认证

---

## 5. 推荐使用场景

### chrome-devtools

- 本地页面加载检查（`http://127.0.0.1:8080/`）
- console error 检查
- network request 检查
- DOM snapshot、页面截图
- **不适合**复用已登录公众号后台

### playwright

- 用户流程测试、表单点击、页面跳转
- 本地 Web UI 验证（多 viewport 回归）
- **不适合**直接复用用户已登录公众号后台（除非另行配置非 isolated profile）

### context7

- 查询 FastAPI、APScheduler、Playwright、SQLAlchemy 等依赖文档
- **不用于**业务数据读取或仓库状态查询

### filesystem

- 读写仓库文件、创建 docs/runbook、搜索代码
- **禁止**写入密钥、cookie、浏览器 profile

### github

- 查仓库、查 issues/PR、必要时创建 PR
- **默认不**主动 push、不建 PR，除非用户明确要求

### stitch

- UI 原型、屏幕生成、私有项目辅助
- **默认不在**普通功能推进轮使用；UI 设计轮再启用

### wechat-chrome-session

- 已登录 `mp.weixin.qq.com` 后台操作
- 定位草稿、核对字段、截图 proof
- 遇到扫码/验证码：**停止并等待用户**

---

## 6. MCP 使用顺序建议

```text
1. 先读 README / AGENTS.md / governance/repo_protocol_standard.yaml
2. 再运行配置检查命令（check_mcp_config.js + check:stitch）
3. 再做当前线程最小探测（每个核心 MCP 至少一次）
4. 再确认浏览器上下文类型（isolated vs 已登录 profile）
5. 再决定使用 chrome-devtools 还是 playwright（本地 Web UI）
6. 再进行本地 Web UI 测试（先 serve，再 navigate）
7. 如涉及公众号已登录后台，必须先确认 wechat-chrome-session 或用户已登录 Chrome CDP 可用
```

**本地 Web UI 启动**：

```bash
python -m wechat_article_scheduler.cli serve
# 默认 http://127.0.0.1:8080/
```

---

## 7. 安全边界

| 禁止项 | 说明 |
|--------|------|
| 不输出 token | 含 `GITHUB_TOKEN`、`STITCH_API_KEY`、微信 AppSecret |
| 不输出 cookie | 含公众号后台 session |
| 不把浏览器 profile 放进仓库 | profile 目录放仓库外或 `.gitignore` |
| 不把 `.env` 提交 | 密钥仅环境变量注入 |
| 不绕过微信公众号扫码登录 | 复用登录态 ≠ 绕过登录 |
| 不绕过验证码 | 停在人工处理处 |
| 不自动点击最终发布 | 发布须用户本人确认 |
| 不做真实发布 | 除非用户明确要求 |

---

## 8. 成功标准

一次 **MCP readiness check** 通过应满足：

- [ ] `node scripts/check_mcp_config.js` → PASS
- [ ] `npm run check:stitch` → PASS
- [ ] 当前线程 tools 可见（非 Multitask 子 Agent）
- [ ] chrome-devtools：`list_pages` 成功
- [ ] playwright：`browser_tabs` list 成功
- [ ] context7：`resolve-library-id` 成功
- [ ] filesystem：`list_allowed_directories` 返回仓库根路径
- [ ] github：`search_repositories` 成功
- [ ] stitch：`list_projects` 成功
- [ ] browser MCP 能打开 `about:blank`（表示实例可用，**不表示已登录**）
- [ ] 无需重启 Cursor
- [ ] 无需额外认证步骤

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [`mcp_tool_matrix.md`](mcp_tool_matrix.md) | 各 MCP 常用工具矩阵 |
| [`browser_context_guide.md`](browser_context_guide.md) | 隔离浏览器 vs 已登录公众号后台 |
| [`mcp_troubleshooting.md`](mcp_troubleshooting.md) | 常见失败与恢复 |
| [`external_agent_browser_notes.md`](external_agent_browser_notes.md) | 外部 Browser Agent 与 MCP 关系 |
| [`../mcp/WORKSPACE_MCP_SERVERS.md`](../mcp/WORKSPACE_MCP_SERVERS.md) | Workspace server 清单 |
| [`../cursor_tool_registry_check.md`](../cursor_tool_registry_check.md) | 线程工具注册表检查 |
| [`../wechat_chrome_session_runbook.md`](../wechat_chrome_session_runbook.md) | 公众号已登录 Chrome 连接 |
