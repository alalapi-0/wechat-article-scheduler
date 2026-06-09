# 浏览器上下文指南

**仓库**：wechat-article-scheduler  
**基线日期**：2026-06-07

本文说明本仓库中 **不同浏览器 MCP 的上下文隔离关系**，避免把 isolated browser 误当作已登录微信公众号后台。

---

## 1. 当前 chrome-devtools / playwright 是 isolated browser

### 基线事实（2026-06-07）

| MCP | 配置 | 探测结果 |
|-----|------|----------|
| chrome-devtools | `npx chrome-devtools-mcp@latest` | `list_pages` → 1 个 `about:blank` |
| playwright | `npx @playwright/mcp@latest --isolated` | `browser_tabs` list → 1 个 `about:blank` |

### 含义

- 它们是 **独立浏览器实例**，由 MCP server 启动或管理
- **不自动共享** 用户本机 Chrome 的登录状态、cookie、扩展或历史记录
- **不能假设** 里面已经登录微信公众号
- `about:blank` 探测成功只表示 **浏览器实例可用**，不表示任何网站已登录

### 适合

- 测试本地 Web 工作台（`http://127.0.0.1:8080/`）
- console / network 检查
- DOM 快照、截图、按钮点击（本地 UI）

### 不适合

- 直接操作用户已登录的 `mp.weixin.qq.com` 后台
- 复用用户 Chrome 中的草稿编辑页
- 代替 `wechat-chrome-session`

---

## 2. 本地 Web UI 测试推荐

### 标准流程

```bash
# 1. 启动服务
python -m wechat_article_scheduler.cli serve

# 2. 用 chrome-devtools 或 playwright 打开
#    http://127.0.0.1:8080/
```

### 必须检查

- 页面是否正常加载（无白屏、无横向溢出）
- **console**：无未处理的 JS error
- **network**：核心 API 无 4xx/5xx
- 关键用户路径：上传、列表、排期、预检、队列等
- 截图或 DOM snapshot 存档（建议 `docs/reports/ui_review/`）

### 工具选择

| 需求 | 推荐 |
|------|------|
| 深查 console / network | chrome-devtools |
| 多 viewport E2E、稳定回归 | playwright |
| 已登录公众号后台 | **均不适用** → 见第 3 节 |

### 禁止

- 用 isolated browser 冒充「已连接用户 Chrome」
- 用 Cursor 内置 `cursor-ide-browser` 的结论替代 Workspace MCP 验证（二者上下文也可能不同）

---

## 3. 微信公众号已登录后台测试

若要 **复用** 用户本人已登录的微信公众号后台，须走以下路线之一：

| 路线 | 说明 |
|------|------|
| **wechat-chrome-session** | `.cursor/mcp.json` 中 `--autoConnect`；用户批准 Chrome 远程调试弹窗 |
| **用户已登录 Chrome + CDP** | Chrome 144+ 开启 `chrome://inspect/#remote-debugging` |
| **持久化 user_data_dir** | Playwright 非 isolated profile（须仓库外目录 + `.gitignore`） |
| **用户手动扫码后继续** | 登录态过期时的正常恢复路径 |

### 安全与合规

- 这是 **复用用户本人正常登录态**，不是绕过登录
- **不导出** cookie 明文
- **不把** cookie 写入项目文件、任务包或发给大模型
- browser **profile 目录** 必须放在仓库外，或加入 `.gitignore`
- **最终发布** 必须由用户本人确认；Agent 停在人机确认处

### 唯一 Workspace MCP

在本仓库中，**只有 `wechat-chrome-session`** 被设计用于连接用户已批准的本机 Chrome。  
`chrome-devtools`（无 `--autoConnect`）和 `playwright --isolated` **不属于** 此路线。

详见 [`docs/wechat_chrome_session_runbook.md`](../wechat_chrome_session_runbook.md)。

---

## 4. 如何判断当前浏览器是否适合公众号后台操作

在操作 `mp.weixin.qq.com` 前，逐项检查：

| 检查项 | 适合后台 | 不适合后台 |
|--------|----------|------------|
| 是否已登录 `mp.weixin.qq.com` | 是 | 否 / 仅 `about:blank` |
| 能否进入内容管理 | 能 | 跳转登录页 |
| 能否进入草稿箱 | 能 | 需要扫码 |
| 是否需要扫码 | 否 | **是 → 停止，等用户** |
| 是否出现验证码 | 否 | **是 → 停止，等用户** |
| 是否是 isolated browser | 否 | **是 → 不能用于后台** |
| 是否可复用 profile / CDP | 是 | 否 |
| 使用的 MCP | `wechat-chrome-session` | `playwright --isolated` / 普通 chrome-devtools |

**决策树**：

```text
需要操作 mp.weixin.qq.com？
├─ 是 → 当前是 wechat-chrome-session 且 list_pages 含已登录标签？
│       ├─ 是 → 可继续（仍须人工确认发布）
│       └─ 否 → BLOCKED；换 wechat-chrome-session 或请用户扫码
└─ 否 → 本地 Web UI → chrome-devtools / playwright isolated 即可
```

---

## 5. 常见误区

| 误区 | 事实 |
|------|------|
| MCP 配置 PASS = 已登录公众号 | 配置 PASS 只说明 server 声明正确；登录态与 MCP 无关 |
| MCP 可用 = 已登录公众号 | 可用只说明工具可调用；`about:blank` 即表示未登录任何站 |
| playwright 可用 = 能复用用户 Chrome 登录态 | 当前 `--isolated`，与用户 Chrome 完全隔离 |
| `about:blank` 成功 = 真实后台可操作 | 只表示浏览器进程起来了 |
| 保存 browser profile = 导出 cookie 明文 | profile 是目录级状态；仍不得把 profile/cookie 提交进 Git |
| 任务包应包含 cookie | **禁止**；任务包只含 prompt、checklist、预览 HTML 等 |
| Multitask 子 Agent 能做浏览器验证 | 子 Agent 通常不继承 Workspace MCP → 假验证 |

---

## 相关文档

- [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md) — MCP readiness 检查
- [`mcp_troubleshooting.md`](mcp_troubleshooting.md) — 公众号后台不可用时的处理
- [`external_agent_browser_notes.md`](external_agent_browser_notes.md) — 外部 Agent 浏览器职责
- [`../cursor_browser_ui_runbook.md`](../cursor_browser_ui_runbook.md) — 本地 UI 验收流程
