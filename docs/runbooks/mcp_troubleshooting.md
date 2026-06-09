# MCP 故障排查

**仓库**：wechat-article-scheduler  
**基线日期**：2026-06-07

本文记录本仓库 MCP 的常见问题、原因与恢复方式。排查时 **不输出** token、cookie、API Key 的具体值。

---

## 1. 配置检查 PASS，但当前线程无工具

### 现象

- `node scripts/check_mcp_config.js` → PASS
- `npm run check:stitch` → PASS
- 当前 Agent 对话中看不到 `list_pages`、`browser_tabs` 等 MCP 工具

### 可能原因

- Cursor 当前 Agent 线程未加载 MCP（旧对话、批准前创建的线程）
- 使用了 **Multitask / 后台子 Agent**（通常不继承 Workspace MCP）
- MCP server 名称变化（线程名如 `project-0-wechat-article-scheduler-chrome-devtools`）
- Settings → Tools & MCP 中 server 未 enabled 或未批准

### 处理

1. **新建普通前台 Agent 对话**（最稳定）
2. 或 **Cmd+Q 完全退出 Cursor** → 重开仓库 → 确认 Tools & MCP 全部 enabled
3. 重新读取 MCP 描述符（`mcps/` 目录或对话内工具列表）
4. 对每个核心 MCP 再做一次最小探测（见 [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md) §3）
5. 仍失败 → 输出 `BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY`

### 不要

- 用 Cursor 内置 `browser_tabs` 假装 Workspace MCP 可用
- 用 `npm run check:cursor-mcp` 的 CLI 结果代替线程探测

---

## 2. chrome-devtools / playwright 只有 about:blank

### 现象

- `list_pages` 或 `browser_tabs` list 只返回 `about:blank`
- 没有 `mp.weixin.qq.com` 或其他已登录页面

### 说明

- **这是正常基线**，表示浏览器实例可用
- **不表示** 已登录任何网站
- 2026-06-07 验证：两者均返回 1 个 `about:blank`

### 处理

| 目标 | 做法 |
|------|------|
| 本地 UI 测试 | 直接 `navigate` 到 `http://127.0.0.1:8080/` |
| 公众号后台 | 改用 `wechat-chrome-session` 或用户 Chrome CDP + 人工批准 |

---

## 3. filesystem 不能读写某路径

### 现象

- `read_file` / `write_file` 报错路径不在允许范围
- 无法访问仓库外目录

### 可能原因

- 路径不在 `list_allowed_directories` 返回的范围内
- 试图读写 `/`、`~`、用户主目录或系统根（被策略禁止）

### 处理

- 只操作 `/Users/alalapi/PycharmProjects/wechat-article-scheduler` 内路径
- 用 `list_allowed_directories` 确认允许目录
- 仓库外文件：除非用户明确允许并另行配置，否则不操作

---

## 4. GitHub 搜索失败

### 现象

- `search_repositories` 返回错误或无结果
- rate limit 或认证失败

### 可能原因

- `GITHUB_TOKEN` / `GITHUB_PERSONAL_ACCESS_TOKEN` 失效或未注入 Cursor 进程
- 网络问题
- GitHub API rate limit

### 处理

1. 记录错误摘要（**不输出 token**）
2. 降级为本地 `git` / `gh` CLI
3. **不自动**重新认证或把 token 写入仓库
4. 确认 token 通过环境变量注入，非 `.cursor/mcp.json` 明文

---

## 5. Stitch 失败

### 现象

- `list_projects` 失败
- `npm run check:stitch` 未通过
- Cursor 显示 stitch 0 tools

### 可能原因

- `STITCH_API_KEY` 缺失、过期或 Cursor 进程未读取到环境变量
- stdio proxy（`scripts/stitch_mcp_proxy.mjs`）未安装依赖
- 网络问题

### 处理

```bash
npm run check:stitch
npm install   # 若 proxy 依赖缺失
```

1. 确认 key 仅通过环境变量设置（**不写入** `.cursor/mcp.json` 或文档）
2. Cmd+Q 退出 Cursor → 重开 → 新建 Agent 线程
3. 只记录错误摘要，**不输出 key**
4. 降级：用 `docs/design/stitch/` 模板 + chrome-devtools/playwright 做 UI 验收

---

## 6. context7 查询失败

### 现象

- `resolve-library-id` 无结果
- `query-docs` 超时或报错

### 可能原因

- 库名不明确（如只写 `sql` 而非 `sqlalchemy`）
- Context7 服务或网络暂时不可用

### 处理

1. 先 `resolve-library-id`，再用返回的 ID 调 `query-docs`
2. 换更具体的库名或版本
3. 降级为官方文档或仓库内 `docs/`
4. **不阻塞**本地项目测试与 mock 模式开发

---

## 7. 公众号已登录后台不可用

### 现象

- 需要操作 `mp.weixin.qq.com` 但页面未登录
- `wechat-chrome-session` 的 `list_pages` 无公众号标签
- 出现扫码页、验证码或风控提示

### 可能原因

| 原因 | 说明 |
|------|------|
| 当前 browser 是 isolated | chrome-devtools / playwright 不能复用用户 Chrome |
| 未使用 wechat-chrome-session | 用了错误的 MCP |
| 没有使用用户 profile | 隔离实例无 cookie |
| 需要扫码 | 登录态过期或未登录 |
| 登录态过期 | 微信 session 超时 |
| 微信后台风控或验证码 | 须人工处理 |

### 处理

1. **停止**自动化操作
2. 切换到 `wechat-chrome-session`（`--autoConnect`）
3. 提示用户在 Chrome 批准远程调试弹窗
4. 若需扫码：等待用户扫码，**不绕过**
5. 若出现验证码：等待用户处理，**不绕过**
6. 可使用持久化 `user_data_dir`（目录放仓库外）
7. 最终发布：**不自动点击**，等用户确认

### 不要

- 用 isolated playwright 新开登录页冒充「已连接用户 Chrome」
- 把 cookie 导出到任务包或发给 LLM
- 在 Multitask 子 Agent 中操作公众号后台

---

## 8. Multitask 子 Agent 浏览器假失败

### 现象

- 主对话 MCP 可用，子 Agent 只有 `browser_tabs` 或无 MCP

### 处理

- 浏览器任务 **必须在普通前台 Agent** 中执行
- 输出 `BLOCKED: MULTITASK_BROWSER_TASK`（见 `.cursor/rules/no-multitask-for-browser.mdc`）
- 请用户禁用 Multitask 后新建对话重试

---

## 9. 修改 mcp.json 后工具未更新

### 处理

1. 运行 `npm run check:mcp && npm run check:stitch`
2. **Cmd+Q 完全退出 Cursor**
3. 重开仓库，Settings → Tools & MCP 确认全部 enabled
4. **新建** Agent 对话
5. 重新做最小探测

---

## 快速参考

| 症状 | 首查文档 | 首选动作 |
|------|----------|----------|
| 线程无工具 | 本文 §1 | 新建前台 Agent 对话 |
| 只有 about:blank | 本文 §2 | 本地 UI：navigate；后台：换 wechat-chrome-session |
| 公众号要登录 | [`browser_context_guide.md`](browser_context_guide.md) | 停止 + 用户扫码 |
| Stitch 0 tools | 本文 §5 | check:stitch + 重启 Cursor |
| 配置与线程不一致 | [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md) | 两层检查都做 |
