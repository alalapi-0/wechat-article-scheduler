# Workspace MCP Servers

| MCP | 用途 | 凭证/边界 |
|---|---|---|
| `chrome-devtools` | 页面、console、network、性能与状态检查 | 不导出 cookie/token |
| `wechat-chrome-session` | 经用户批准连接已登录 Chrome 的公众号后台 | 仅已确认 manifest，保留 proof |
| `context7` | 查询第三方库与框架文档 | 优先官方/一手资料 |
| `filesystem` | 读写当前项目文件 | 仅 `${workspaceFolder}` |
| `github` | 仓库、issue、PR、分支与 CI | `GITHUB_TOKEN` 环境变量 |
| `playwright` | 浏览器自动化与 E2E | 默认隔离会话 |
| `stitch` | UI 设计系统、原型、screen、截图和 HTML | `STITCH_API_KEY` 环境变量；本地 stdio proxy（`scripts/stitch_mcp_proxy.mjs`）；只作设计输入 |

## Stitch 配置要点

- **Remote MCP**（`url` + header）与 **Local stdio proxy**（`node scripts/stitch_mcp_proxy.mjs`）两种方式均指向 `https://stitch.googleapis.com/mcp`；本项目采用 **stdio proxy**，server 名称为 `stitch`。
- Key 只通过 `${env:STITCH_API_KEY}` 注入，不得写入 `.cursor/mcp.json`。
- 验证：`cursor-agent mcp list-tools stitch` 须返回非空 tools；`No tools/prompts/resources` 视为不可用。
- 修改 MCP 后：**Cmd+Q 完全退出 Cursor** → 重开仓库 → Settings → Tools & MCP 检查 `stitch` → **新建普通前台 Agent**。
- Stitch 不可用时：用 `docs/design/stitch/` 模板 + chrome-devtools / playwright 做 UI 验收。

## 任务映射

- 新 UI / 页面方案：先读 `docs/design/`，优先 Stitch。
- 页面实现验收：Playwright；需要 console/network 深查时用 chrome-devtools。
- 第三方 API/框架疑问：context7 或官方文档。
- GitHub 操作：先 `git status` 与 `git diff`，再使用 GitHub MCP。
- 本地文件：filesystem 或等效工具，禁止扩大到用户主目录或系统根目录。

## 降级

单个 MCP 不可用时记录原因，使用仓库脚本、官方文档或本地工具继续。Stitch 不可用时使用设计模板；Playwright MCP 不可用时可用 Python Playwright 测试。只有当前子任务唯一依赖某凭证且无替代路径时才阻塞。

## 安全

- 不读取或打印 `.env`。
- 不把 key、token、cookie、session 写入配置、文档、日志或产物。
- 不用 Stitch 导出代码直接覆盖业务代码。
- 不用浏览器 MCP 绕过登录、验证码、平台风控或最终发布确认。
