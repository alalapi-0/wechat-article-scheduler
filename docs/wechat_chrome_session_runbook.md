# wechat-chrome-session 操作手册

Status: Current — 手动登录门控 + 已登录 Chrome 复用

## 适用场景

- 用户**必须在场**确认扫码登录
- Cursor Agent 需要在**已授权**的 Chrome 会话中辅助核对公众号后台字段
- 不得使用 Playwright `--isolated` 会话冒充已登录态

## MCP 配置

仓库 `.cursor/mcp.json` 中 `wechat-chrome-session` 使用 `chrome-devtools-mcp` 的 `--autoConnect` 模式：

- 连接用户已开启远程调试的 Chrome
- `--redactNetworkHeaders` 避免 network 头泄露
- **不**读取或导出 cookie

普通 `playwright` 与 `chrome-devtools` 使用独立 profile，**不会**继承日常 Chrome 登录态。

## 启动 Chrome 远程调试（推荐独立 profile）

1. 使用**仅登录公众号**的 Chrome profile（勿与银行/邮箱混用）。
2. Chrome 144+ 打开 `chrome://inspect/#remote-debugging` 并开启远程调试。
3. 打开 [微信公众平台](https://mp.weixin.qq.com/) 草稿箱标签页。
4. 在 Cursor **Tools & MCP** 确认 `wechat-chrome-session` 已加载。
5. 首次连接时在 Chrome 弹窗中**允许**调试连接。

可选：使用仓库外 `user_data_dir` 启动专用 Chrome（路径勿放入仓库）：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$HOME/.wechat-mp-chrome-profile" \
  --remote-debugging-port=9222
```

Agent **不得**读取 `.env`、不得导出 cookie、不得保存密码。

## 与本项目联动的手动流程

### 1. 启动 browser_assist 会话（登录门控）

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-session start --job-id <JOB_ID>
```

或 Web 作品详情页 → **浏览器辅助（手动登录）** → **开始浏览器辅助**。

返回 `awaiting_browser_login` 并提示：

> 请在本浏览器窗口扫码登录，完成后点击「已登录，继续」。

### 2. 用户扫码登录

- 用户在 Chrome 窗口完成微信扫码
- Agent 仅可 `list_pages` / 截图只读核对，**不得**代填账号密码

### 3. 确认已登录

CLI：

```bash
python -m wechat_article_scheduler.cli browser-assist-session confirm-login --session-id <SESSION_ID>
```

Web：点击 **已登录，继续**。

状态变为 `assist_in_progress`。此时 Agent 可在已登录页执行 task 包 checklist（定位草稿、核对字段、辅助设置定时时间）。

### 4. 设置后台定时（非最终确认）

Agent 可辅助填写公众号后台定时时间，**不得**点击最终定时群发确认。

确认已设置：

```bash
python -m wechat_article_scheduler.cli browser-assist-session confirm-schedule-setup --session-id <SESSION_ID>
```

### 5. 用户最终定时确认（仅人类）

用户必须在公众号后台**亲自**点击最终定时群发确认。Agent 停止并等待 attestation：

```bash
python -m wechat_article_scheduler.cli browser-assist-session confirm-final-schedule --session-id <SESSION_ID>
```

### 6. 回填 proof

```bash
python -m wechat_article_scheduler.cli submit-proof --job-id <JOB_ID> --screenshot-path ...
```

或 Web 作品详情 `#proof`。

## 如何验证已登录

Agent 或用户可核对：

- URL 不在 login / 扫码页
- 可见公众号后台导航或草稿箱列表
- 用户本人 attestation（本项目记录 `login_confirmed_at`）

**不**通过读取 cookie 或 `.env` 验证。

## 安全边界

| 允许 | 禁止 |
|------|------|
| 连接用户已批准的 Chrome 调试会话 | 导出/保存 cookie |
| 只读 list_pages、截图 | 读取 `.env` / token |
| 辅助填写非最终字段 | 绕过扫码/验证码 |
| 设置后台定时时间 | Agent 点击最终定时确认或最终发布 |
| 用户 attestation 后继续 | 无人值守 weekly 自动发布 |

## 相关文档

- `docs/browser_assist_runbook.md`
- `docs/external_agent_integration_guide.md`
- `docs/agent_skills/mcp_usage_skill.md`
