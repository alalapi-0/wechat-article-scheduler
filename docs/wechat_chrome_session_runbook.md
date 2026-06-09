# wechat-chrome-session 操作手册

Status: Current — 唯一真实浏览器路线：`wechat-chrome-session --autoConnect`

## 适用场景

- 用户**必须在场**批准 Chrome 调试连接；仅在登录过期时扫码登录
- Cursor Agent 需要在**已授权**的 Chrome 会话中辅助核对公众号后台字段
- 不得使用 Playwright `--isolated` 会话冒充已登录态

## 直接交给 Cursor Agent 的任务说明

用户可以把本文件完整发送给 Cursor Agent，并附上这一句话：

```text
请严格执行 docs/wechat_chrome_session_runbook.md 的“阶段 A 到阶段 D”。
当前只验证你能否接管我已经登录的微信公众号 Chrome 标签页：
必须使用 wechat-chrome-session，完成 list_pages、选择 mp.weixin.qq.com 页面、
DOM snapshot 和截图，输出脱敏连接报告后停止。
不要修改草稿，不要点击保存、删除、发布或最终定时确认。
```

Agent 的第一目标不是发布，而是独立证明以下四件事：

1. Cursor 已加载 `wechat-chrome-session` MCP。
2. MCP 连接的是用户正在运行的 Chrome，不是新开的隔离浏览器。
3. Agent 能找到现有的 `mp.weixin.qq.com` 标签页。
4. Agent 能读取该标签页的可见 DOM 并截图。

上述四项没有全部通过时，不得进入草稿操作。

## Cursor 对话模式要求

真实 Chrome 接管任务必须在普通前台 **Agent** 对话中执行：

- 不得使用 `/multitask` 或输入框中的 **Multitask** 标签。
- 不得把任务交给异步子 Agent；子 Agent 可能不继承 workspace MCP 工具。
- 在输入框的工具菜单中确认 MCP tools 已启用，且 `wechat-chrome-session` 的工具没有被关闭。
- 切换模式或工具后新建普通 Agent 对话，再执行阶段 A。

如果输入框左下方显示紫色 `Multitask ×` 标签，先点击 `×` 移除，再发送任务。

## 阶段 A：检查仓库和 MCP

Agent 在仓库根目录执行：

```bash
npm run check:mcp
```

输出必须包含：

```text
wechat-chrome-session
```

这一步只证明 `.cursor/mcp.json` 有效，不代表 Cursor 当前会话已经加载 MCP。

继续检查 Cursor 的实际加载与批准状态：

```bash
cursor-agent mcp list
cursor-agent mcp list-tools wechat-chrome-session
```

`wechat-chrome-session` 必须显示为已加载，并且工具列表应包含 `list_pages`、`select_page`、snapshot、screenshot 等 Chrome DevTools 工具。

若显示：

```text
wechat-chrome-session: not loaded (needs approval)
```

由用户在 Cursor **Settings -> Tools & MCP** 中批准并启用 `wechat-chrome-session`，或由用户本人在终端执行：

```bash
cursor-agent mcp enable wechat-chrome-session
```

然后执行 **Developer: Reload Window**。若当前 Agent 仍报告 `MCP server does not exist`，必须：

1. `Cmd+Q` 完全退出 Cursor。
2. 重新打开本仓库。
3. 在 **Settings -> Tools & MCP** 确认 `wechat-chrome-session` 为 ready。
4. 新建 Agent 对话；不得继续复用批准前已经打开的旧对话。
5. 再次运行上述两条检查命令。

`cursor-agent mcp list` 显示 `ready` 只说明 CLI 能加载配置；旧编辑器窗口或旧 Agent 对话仍可能保留批准前的工具注册表。批准 MCP 是用户授权动作，Agent 不得自行绕过。

Agent 继续检查自己当前可调用的 MCP 工具：

- 存在 `wechat-chrome-session`：进入阶段 B。
- 不存在：停止并要求用户执行 **Reload Window** 或重启 Cursor。
- Cursor 的 **Settings -> Tools & MCP** 中该 server 必须为可用状态。

工具验收必须看“调用来源”，不能只看动作名称：

- 合格：调用来源明确属于 `wechat-chrome-session`，并提供 `list_pages`、`select_page`、snapshot、screenshot。
- 不合格：调用 Cursor 内置 `browser_tabs` 后只能看到 localhost 预览页。
- 不合格：调用普通 `chrome-devtools` 或 `playwright` 后列出它们自己的独立浏览器页面。

若 Agent 的工具面板中根本没有 `wechat-chrome-session` 对应工具，即使 `npm run check:mcp` 显示配置存在，也必须报告 `BLOCKED: MCP_NOT_LOADED`，不得继续。

若 server 已连接、CLI 能列出工具，但 Multitask 子线程报告
`MISSING_FROM_THREAD_TOOL_REGISTRY`，应退出 Multitask，改用普通前台 Agent；
不得重命名 server 或修改 Chrome 连接参数。

Agent 不得在 `wechat-chrome-session` 缺失时改用：

- Cursor 内置 `browser_tabs`
- `playwright --isolated`
- 普通 `chrome-devtools`
- 新启动的临时 Chrome profile

这些入口通常拿不到用户当前公众号登录态。

## 阶段 B：用户开启现有 Chrome 调试

以下步骤需要用户本人完成：

1. 在已经登录公众号的同一个 Chrome profile 中打开：

   ```text
   chrome://inspect/#remote-debugging
   ```

2. 开启远程调试。
3. 保持目标 `mp.weixin.qq.com` 标签页打开。
4. 不使用无痕窗口。
5. 暂时关闭银行、邮箱、密码管理器等无关敏感标签页。
6. Chrome 出现调试连接授权提示时，由用户点击允许。

当前机器 Chrome 版本已经满足 `--autoConnect` 所需版本。Agent 不需要用户提供 cookie、密码、二维码或 token。

如果用户是在 Cursor 启动后才开启远程调试，Cursor Agent 应重启 `wechat-chrome-session` MCP；必要时 Reload Window。

## 阶段 C：连接并找到现有页面

Agent 必须明确选择 `wechat-chrome-session` MCP。

不同 Cursor 版本显示的工具名前缀可能不同，但执行顺序必须等价于：

1. `list_pages`
2. 从返回结果中查找 host 为 `mp.weixin.qq.com` 的页面
3. `select_page`
4. `take_snapshot` 或等价 DOM snapshot
5. `take_screenshot`

操作规则：

- 第一次 `list_pages` 只读取标题和 URL，不点击页面。
- URL 输出前必须移除 query 和 fragment。
- 可以输出：

  ```text
  https://mp.weixin.qq.com/cgi-bin/home
  ```

- 不得输出：

  ```text
  token=...
  ```

- 找到多个公众号页面时，只列出脱敏标题和 path，让用户指定；Agent 不自行猜测账号。
- 没找到页面时，不要连续重试。按“连接故障排查”检查后最多再调用一次 `list_pages`。

如果 Agent 调用后打开的是新 Chrome、空白页或登录页，说明选错了 MCP/profile，不能算连接成功。

## 阶段 D：只读验收并停止

Agent 对目标页面做以下只读检查：

- 页面标题与微信公众号后台一致。
- URL host 是 `mp.weixin.qq.com`。
- 页面不是扫码登录页、验证码页或安全验证页。
- 页面可见公众号后台导航、首页或草稿箱入口。
- DOM snapshot 和截图来自同一个目标标签页。
- 没有执行点击、填写、保存、删除或发布。

然后输出下面格式的报告：

```text
真实 Chrome 会话连接报告

- MCP: wechat-chrome-session
- Connection mode: existing Chrome / autoConnect
- Target host: mp.weixin.qq.com
- Page title: <脱敏标题>
- Backend visible: yes/no
- Login required: yes/no
- DOM snapshot available: yes/no
- Screenshot available: yes/no
- Write actions performed: 0
- Result: PASS/BLOCKED
- Block reason: <没有则写 none>
```

报告输出后停止。只有用户看过 PASS 报告并明确允许，才进入后面的单篇草稿测试。

## 连接故障排查

### 配置检查通过，但 Cursor 没有这个 MCP

原因通常是 Cursor 尚未重新加载 workspace MCP。

处理顺序：

1. 确认 Cursor 打开的 workspace 根目录是本仓库。
2. Reload Window。
3. 检查 Settings -> Tools & MCP。
4. 查看 `wechat-chrome-session` 启动日志。

在 server 可用前不得继续浏览器操作。

### `list_pages` 返回空列表

依次确认：

1. `chrome://inspect/#remote-debugging` 的开关仍然开启。
2. Chrome 的连接授权弹窗没有被拒绝。
3. 公众号页面在普通窗口中。
4. 开启远程调试的是公众号所在的同一个 Chrome profile。
5. Cursor 已在开启调试后重启该 MCP。

检查完成后最多重试一次。仍为空则报告 BLOCKED。

### Agent 打开了新的空白 Chrome

说明 Agent 使用了错误入口，常见原因：

- 使用普通 `chrome-devtools`
- 使用 `playwright --isolated`
- 没有使用 `--autoConnect`

Agent 应停止错误的浏览器会话，重新选择 `wechat-chrome-session`。不得通过在新浏览器中重新登录来掩盖连接失败。

### 找到微信页面，但显示扫码登录

通常说明连接到了错误 profile。

Agent 应检查 MCP 名称与 Chrome profile，不得读取二维码、代替用户扫码或要求用户提供密码。

### MCP 报站点或安全策略禁止

这属于 Cursor、MCP 或浏览器工具自身的安全边界，不是本仓库代码问题。

Agent 必须：

1. 停止操作。
2. 报告被禁止的是 `list_pages`、`select_page`、snapshot、截图还是点击阶段。
3. 不改用原始 CDP 脚本、AppleScript、键鼠模拟或其他工具绕过。

### 页面能看见，交互后失去控制

Agent 立即停止写操作，重新执行一次页面列表和 snapshot。若出现重新登录、验证码、账号变化或平台警告，交还用户处理。

## MCP 配置

仓库 `.cursor/mcp.json` 中 `wechat-chrome-session` 使用 `chrome-devtools-mcp` 的 `--autoConnect` 模式：

- 连接用户已开启远程调试的 Chrome
- `--redactNetworkHeaders` 避免 network 头泄露
- **不**读取或导出 cookie

普通 `playwright` 与 `chrome-devtools` 使用独立 profile，**不会**继承日常 Chrome 登录态。

本项目不再提供专用 `9222` profile、CDP 状态 CLI、二维码缓存或项目内登录辅助页。连接真实页面的唯一入口是 Cursor 加载的 `wechat-chrome-session --autoConnect`。

## 与本项目联动的手动流程

### 1. 启动 browser_assist 会话（登录门控）

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-session start --job-id <JOB_ID>
```

或 Web 作品详情页 → **浏览器辅助（手动登录）** → **开始浏览器辅助**。

返回 `awaiting_browser_login` 并提示：

> 请在本浏览器窗口扫码登录，完成后点击「已登录，继续」。

### 2. 连接现有已登录页面

- Agent 按阶段 A 到阶段 D 连接用户当前 Chrome
- 若页面已经登录，直接进行只读验收
- 只有登录过期时，才由用户在可见 Chrome 页面自行扫码
- Agent 仅可 `list_pages` / 截图只读核对，**不得**代填账号密码

### 3. 确认已登录

先把阶段 D 的连接验收报告回填到当前会话（示例）：

```bash
python -m wechat_article_scheduler.cli browser-assist-session record-connection \
  --session-id <SESSION_ID> \
  --report-json '{"mcp":"wechat-chrome-session","connection_mode":"existing Chrome / autoConnect","target_host":"mp.weixin.qq.com","target_url":"https://mp.weixin.qq.com/cgi-bin/home","page_title":"公众号后台（脱敏）","backend_visible":true,"login_required":false,"dom_snapshot_available":true,"screenshot_available":true,"write_actions_performed":0,"result":"PASS","block_reason":"none"}'
```

若报告结果为 `BLOCKED`，必须先解决阻塞项；不得直接确认登录。

CLI：

```bash
python -m wechat_article_scheduler.cli browser-assist-session confirm-login --session-id <SESSION_ID>
```

Web：点击 **已登录，继续**。

状态变为 `assist_in_progress`。此时 Agent 可在已登录页执行 task 包 checklist（定位草稿、核对字段、辅助设置定时时间）。

### 4. 准备并保存草稿

Agent 可定位草稿，核对标题/摘要/封面/正文，设置合集、通知、封面显示和目标时间，然后点击“保存草稿”。保存后必须重新打开同一草稿，核验字段是否持久化。

Agent **不得**点击正式发表、群发或创建真实定时任务的最终确认，也不得处理二维码或手机确认。

记录草稿检查完成：

```bash
python -m wechat_article_scheduler.cli browser-assist-session confirm-schedule-setup --session-id <SESSION_ID>
```

> `confirm-schedule-setup` 是历史兼容命令名，表示“发布前草稿准备完成，等待 proof”，不表示已经正式发表或创建后台定时任务。

### 5. 最终发表与安全验证（仅人类）

用户打开 Agent 已准备并保存的草稿，点击最终发表/定时确认并完成扫码、手机确认或管理员验证。若目标时间不能随保存草稿持久化，用户按 manifest 在这一步回填。

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
| 设置发布前字段、保存草稿、重新打开核验 | 绕过扫码/验证码 |
| 记录目标时间和持久化结果 | Agent 点击最终定时确认或最终发布 |
| 用户 attestation 后继续 | 无人值守 weekly 自动发布 |

## 相关文档

- `docs/browser_assist_runbook.md`
- `docs/wechat_scheduled_publish_browser_test.md`
- `docs/external_agent_integration_guide.md`
- `docs/agent_skills/mcp_usage_skill.md`
