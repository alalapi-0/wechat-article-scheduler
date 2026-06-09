# MCP 工具矩阵

**仓库**：wechat-article-scheduler  
**基线日期**：2026-06-07  
**说明**：本表列出仓库 **常用** MCP 工具及其边界，非完整 schema。完整参数见 Cursor 对话中的 MCP 描述符或 `mcps/` 目录。

---

## chrome-devtools（29 tools）

线程名：`project-0-wechat-article-scheduler-chrome-devtools`  
浏览器上下文：**隔离实例**（非用户本机已登录 Chrome）

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| chrome-devtools | `list_pages` | 列出当前浏览器中打开的页面 | 任务开始前确认浏览器实例可用 | 返回 `about:blank` 正常，不表示已登录任何网站 | `list_pages` → 至少 1 页 |
| chrome-devtools | `navigate_page` | 导航到指定 URL | 打开 `http://127.0.0.1:8080/` 做本地 Web UI 检查 | 不要用于假设已登录 `mp.weixin.qq.com` | navigate 到 localhost |
| chrome-devtools | `take_snapshot` | 获取页面 DOM / 可访问性快照 | UI 改版前后对比、元素定位 | 快照不含 cookie；不代替真实用户路径验证 | 对 serve 后首页 take_snapshot |
| chrome-devtools | `list_console_messages` | 列出 console 消息 | 检查 JS error、warning | 须结合 network 一起看 | serve 后 list_console_messages |
| chrome-devtools | `list_network_requests` | 列出网络请求 | 检查核心 API 4xx/5xx | 不打印含 token 的 header 值 | 操作后 list_network_requests |

---

## playwright（23 tools）

线程名：`project-0-wechat-article-scheduler-playwright`  
浏览器上下文：**`--isolated` 隔离实例**

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| playwright | `browser_tabs` | 列出 / 创建 / 选择 / 关闭标签页 | 任务开始前确认实例可用 | `action=list` 返回 `about:blank` 为正常基线 | `browser_tabs` action=list |
| playwright | `browser_navigate` | 导航到 URL | 本地 Web UI E2E、多 viewport 回归 | 隔离实例无用户 Chrome 登录态 | navigate 到 `http://127.0.0.1:8080/` |
| playwright | `browser_snapshot` | 获取页面可访问性快照 | 定位按钮、表单、链接 | 须走真实用户路径，不能只看快照 | 首页 browser_snapshot |
| playwright | `browser_click` | 点击页面元素 | 表单提交、Tab 切换、按钮操作 | 不要在未确认上下文时点击公众号「发布」 | 点击工作台导航项 |
| playwright | `browser_console_messages` | 获取 console 输出 | 回归检查 JS 错误 | 与 network 检查配合使用 | 操作后 browser_console_messages |

---

## context7（2 tools）

线程名：`project-0-wechat-article-scheduler-context7`

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| context7 | `resolve-library-id` | 将库名解析为 Context7 库 ID | 查询前先解析，避免库名歧义 | 不用于业务数据或仓库文件 | `libraryName=fastapi` |
| context7 | `query-docs` | 查询已解析库的文档 | FastAPI、Playwright、APScheduler、SQLAlchemy 等 | 网络失败不阻塞本地测试；先 resolve 再 query | resolve 后 query-docs |

---

## filesystem（14 tools）

线程名：`project-0-wechat-article-scheduler-filesystem`  
允许目录：`/Users/alalapi/PycharmProjects/wechat-article-scheduler`

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| filesystem | `read_file` | 读取仓库内文件 | 读代码、docs、配置示例 | 不读 `.env`；不读仓库外路径 | 读 `README.md` |
| filesystem | `write_file` | 写入仓库内文件 | 创建 runbook、更新 docs | 不写密钥、cookie、browser profile | 写 `docs/runbooks/*.md` |
| filesystem | `list_directory` | 列出目录内容 | 探索目录结构 | 仅限允许目录 | `list_directory` 根目录 |
| filesystem | `search_files` | 按模式搜索文件 | 定位源码、测试、文档 | 不搜索用户主目录或系统根 | 搜索 `*runbook*` |

---

## github（26 tools）

线程名：`project-0-wechat-article-scheduler-github`  
认证：环境变量 `GITHUB_TOKEN` / `GITHUB_PERSONAL_ACCESS_TOKEN`（已生效，勿输出值）

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| github | `search_repositories` | 搜索 GitHub 仓库 | 确认远程仓库存在、查同类项目 | 不输出 token；注意 rate limit | 搜索 `alalapi-0/wechat-article-scheduler` |
| github | `list_issues` | 列出 issue | 查已知问题、推进状态 | 默认不主动创建 issue | 列出本仓库 open issues |
| github | `create_pull_request` | 创建 PR | **仅**用户明确要求时 | 提交前必须 `git diff`；不把密钥放进 PR body | 一般不用于探测 |

---

## stitch（15 tools）

线程名：`project-0-wechat-article-scheduler-stitch`  
认证：`STITCH_API_KEY` 环境变量（已生效，勿输出值）

| Server | Tool | 用途 | 适合场景 | 禁止或注意事项 | 示例探测 |
|--------|------|------|----------|----------------|----------|
| stitch | `list_projects` | 列出 Stitch 私有项目 | 确认 Stitch 连通、选设计项目 | 不输出 API key | `list_projects` |
| stitch | `generate_screen_from_text` | 从文本生成 UI screen | UI 设计轮、新页面原型 | 导出物只进 `docs/design/stitch/`；不覆盖 `src/` | 设计轮使用 |
| stitch | `get_screen` | 获取已有 screen 详情 | 读取设计输入、截图、HTML | 须经审查后再实现到业务代码 | 设计轮使用 |

---

## wechat-chrome-session（公众号后台，配置已声明）

**不在 2026-06-07 六项基线探测范围内**；操作公众号后台前须单独探测。

| 代表工具 | 用途 | 适合场景 | 禁止或注意事项 |
|----------|------|----------|----------------|
| `list_pages` | 列出用户 Chrome 中打开的页面 | 确认能看到 `mp.weixin.qq.com` | 唯一适合复用已登录后台的 Workspace MCP |
| `select_page` | 选择目标标签页 | 切换到公众号编辑页 | 遇扫码/验证码停止 |
| `take_snapshot` / `navigate_page` | 页面操作与检查 | 定位草稿、核对字段 | 不点击最终发布；不导出 cookie |

详见 [`browser_context_guide.md`](browser_context_guide.md) 与 [`../wechat_chrome_session_runbook.md`](../wechat_chrome_session_runbook.md)。

---

## 工具选择速查

| 任务类型 | 首选 MCP | 备选 |
|----------|----------|------|
| 本地 Web UI 调试 | chrome-devtools | playwright |
| 本地 Web UI E2E | playwright | chrome-devtools |
| 依赖库文档 | context7 | 官方文档 |
| 读写仓库文件 | filesystem | 内置 Read/Write 工具 |
| GitHub 操作 | github | 本地 `git` / `gh` |
| UI 设计输入 | stitch | `docs/design/stitch/` 模板 |
| 公众号已登录后台 | wechat-chrome-session | 用户 Chrome + CDP（须人工批准） |
