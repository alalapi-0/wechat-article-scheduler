# MCP 工具使用技能（Agent 自动推进轮）

本文档说明本仓库 `.cursor/mcp.json` 中启用的 MCP 服务器、用途、授权范围与降级策略。Agent 自动推进轮开始前应阅读本文档，并在 Cursor **Tools & MCP** 中确认相关 server 已加载。

## 当前启用的 MCP

| MCP | 用途 | 是否必需 token |
|-----|------|----------------|
| **playwright** | 浏览器自动化：打开页面、点击、填表、截图、基本 UI 交互与 E2E 验收 | 否 |
| **chrome-devtools** | DevTools 级调试：console 日志、network 请求、性能分析 | 否 |
| **wechat-chrome-session** | 经用户批准后连接已运行、已登录的 Chrome，用于公众号后台任务 | 否 |
| **context7** | 查询第三方库/框架最新文档（prompt 中可写 `use context7`） | 否（可选 API Key 见下文） |
| **filesystem** | 受控读写项目内文件，确认真实文件状态 | 否 |
| **github** | 读取仓库、提交记录、issue、PR、CI 状态 | 是（`GITHUB_TOKEN`） |
| **stitch** | UI 设计系统、原型、screen、截图与 HTML 导出 | 是（`STITCH_API_KEY`） |

配置位置：`.cursor/mcp.json`。修改后通常需要 **重启 Cursor** 才会重新加载。

## Playwright MCP

**用于什么：**

- 打开本地 Web 工作台（`python -m wechat_article_scheduler.cli serve` → `http://127.0.0.1:8080/`）
- 走真实用户路径：上传、排期、批量发布设置、刷新确认持久化
- 配合 chrome-devtools 检查 **console** 与 **network**
- 辅助 E2E 验收；不能替代 `python scripts/agent_gate.py gate` 与 pytest

**浏览器检查必须包含：**

1. 打开目标页面（不是只看代码或单张截图）
2. 执行至少一条核心用户流程
3. 检查 console（无 error；warning 需记录）
4. 检查 network（核心 API 无 4xx/5xx）
5. 必要时保存 snapshot / screenshot 佐证 UI 变化

涉及前端、Web 工作台、文件上传/删除、API 调用时，优先 **Playwright MCP**，需要深层 console/network 时用 **Chrome DevTools MCP**。详见 `.cursor/skills/browser-debug-check/SKILL.md` 与 `.cursor/rules/verification-gate.mdc`。

### 已登录公众号 Chrome 会话

`playwright` 当前使用 `--isolated`，不会继承日常 Chrome 登录态。`chrome-devtools` 默认也会使用自己的专用 profile。需要 Cursor Agent 操作用户已经登录的公众号后台时，使用单独的 `wechat-chrome-session`：

1. 使用 Chrome 144 或更高版本打开 `chrome://inspect/#remote-debugging`。
2. 开启远程调试。
3. 保持要操作的 `mp.weixin.qq.com` 标签页打开。
4. 重启或重新加载 Cursor MCP。
5. Cursor 第一次连接时，用户在 Chrome 弹窗中选择允许。
6. Agent 先执行 `list_pages` 和只读截图，确认账号与页面；不得直接开始批量写操作。

该 MCP 使用 `--autoConnect`，可访问所选 Chrome profile 的所有窗口和标签页。操作前应关闭银行、邮箱、密码管理器等无关敏感页面；更稳妥的长期方案是使用只登录公众号的独立 Chrome profile。

公众号后台操作必须遵守：

- 同一时间只允许一个 Agent 控制该会话。
- 第一次运行只做 1 篇草稿的 dry-run。
- 批量运行前生成 manifest，用户确认标题、目标时间、合集和数量。
- 只操作 manifest 中的草稿；页面结构、账号、数量或时间不一致时立即停止。
- 不读取或导出 cookie、密码、二维码、Authorization 或请求头。
- 每篇操作后截图或记录后台状态；无 proof 不得标记完成。
- 最终定时确认属于真实发布副作用，必须有本批次用户确认。

## 文件系统 MCP 授权范围

filesystem server 仅授权 **当前项目根目录**：

```json
"args": ["-y", "@modelcontextprotocol/server-filesystem", "${workspaceFolder}"]
```

- `${workspaceFolder}` 解析为包含 `.cursor/mcp.json` 的仓库根目录
- **禁止**授权 `/`、`C:\`、用户主目录根路径或整个磁盘
- Agent 删除/移动文件前必须用 filesystem 或 shell 确认真实路径与状态
- 测试 destructive 操作时仅使用 mock 数据或测试目录（默认 `WECHAT_MODE=mock`）

## GitHub MCP 与 token

GitHub MCP 通过环境变量注入 token，**不写入仓库**：

```json
"env": {
  "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_TOKEN}"
}
```

**本地配置（任选其一）：**

```bash
export GITHUB_TOKEN=ghp_xxxxxxxx   # 推荐变量名
# 或
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxx
```

若使用第二种变量名，可将 `mcp.json` 中 `${env:GITHUB_TOKEN}` 改为 `${env:GITHUB_PERSONAL_ACCESS_TOKEN}`（仅本地，勿提交真实 token）。

**所需权限（按需）：** `repo`（私有库）或 `public_repo`（仅公开库），以及读取 issue/PR 的 scope。

**无 token 时的降级：**

- 使用 `git log`、`git status`、`git diff` 等本地 git 命令
- 使用 `gh` CLI（若已登录）读取 PR/issue
- 记录「GitHub MCP 不可用：缺少 GITHUB_TOKEN」，**不要**因此阻塞不涉及 GitHub API 的整轮推进

## Context7（文档查询）

已启用 `@upstash/context7-mcp`。用于查询 FastAPI、Playwright、SQLite 等库的最新文档。

- 无 API Key 时通常仍可用基础查询；若 server 启动失败，降级为阅读项目 `docs/`、`README.md` 与官方文档网页
- **不要**在仓库中提交 Context7 API Key

## Stitch（UI 设计输入）

涉及新页面、审核台、预览页、管理后台或 debug 页面时，先读 `docs/design/DESIGN.md` 与 `docs/design/stitch/`。`stitch` 使用 Remote MCP，通过 `${env:STITCH_API_KEY}` 注入认证；导出物保存到 `docs/design/stitch/`。

Stitch 只提供设计输入。Agent 必须评审并拆分设计，再按当前 `FastAPI + 原生 HTML/CSS/JS` 技术栈实现；不得无审查覆盖业务代码。实现后仍须 Playwright 或 chrome-devtools 验证。

## 没有 API Key / token 时的通用降级

| 能力 | 降级方案 |
|------|----------|
| Playwright / Chrome DevTools | Python Playwright 测试、`tools/browser_automation/ui_review.py`、`pytest tests/test_ui_e2e.py` |
| filesystem | Cursor 内置 Read/Write/Grep 工具 + `git status` |
| GitHub MCP | 本地 `git` / `gh` CLI |
| Context7 | 项目文档 + 官方文档 URL |
| Stitch | `docs/design/stitch/` 中的任务与 prompt 模板 |
| 真实微信 API | 保持 `WECHAT_MODE=mock`，记录原因后继续 mock/dry-run |

唯一阻塞：当前任务**必须**依赖某 token 且无任何替代路径时，才暂停该子任务并记录。

## 后续自动推进轮如何使用

推荐循环：

1. `python scripts/agent_gate.py status` — 当前轮次与验收项
2. `npm run check:mcp` 或 `node scripts/check_mcp_config.js` / `python scripts/check_mcp_config.py` — MCP 配置摘要与安全检查
3. 确认 Cursor 中 MCP 已加载（Settings → Tools & MCP）
4. 实现任务；UI 相关必须 Playwright + console/network 验证
5. `python scripts/agent_gate.py gate` — pytest + 轮次冒烟
6. 提交前 `git diff`，确认无 `.env`、密钥、token
7. `python scripts/agent_gate.py advance --commit`（是否 push 按轮次策略）

Prompt 示例：

```text
请按 docs/agent_skills/mcp_usage_skill.md 确认 MCP，并用 Playwright 验证 http://127.0.0.1:8080/ 作品库上传流程
```

```text
use context7 查询 FastAPI File Upload 最新用法
```

## 安全禁止事项

1. **禁止**提交 token、cookie、API Key、session 到 git
2. **禁止**在 `mcp.json` 中写死 `ghp_`、`sk-` 等密钥；只用 `${env:...}`
3. **禁止** filesystem MCP 授权系统根目录或用户主目录
4. **禁止**日志打印 access token / secret / `.env` 内容
5. **禁止**在没有当前批次 manifest 和用户确认时操作真实公众号；已确认任务只能使用 `wechat-chrome-session`，且必须留 proof
6. **禁止**仅凭代码静态阅读或单张截图判断 UI 任务完成

## 验证命令

```bash
# MCP 配置检查
npm run check:mcp
npm run check:stitch
# 或
node scripts/check_mcp_config.js
python scripts/check_mcp_config.py

# JSON 格式（需 jq 或 python）
python -c "import json; json.load(open('.cursor/mcp.json'))"

# 项目门禁
python scripts/agent_gate.py gate
```

修改 `.cursor/mcp.json` 后请 **重启 Cursor** 再验证 MCP 是否出现在 Tools & MCP 列表中。

## 相关文件

- `.cursor/mcp.json` — MCP 服务器声明
- `AGENTS.md` — Agent 入口与 MCP Tools 节
- `.cursor/rules/mcp-agent-tools.mdc` — MCP 使用规则
- `.cursor/rules/verification-gate.mdc` — 浏览器验证门禁
- `.cursor/rules/stitch-design-mcp.mdc` — Stitch 设计输入规则
- `docs/design/stitch/` — Stitch 配置、工作流、模板与导出规范
- `docs/agent-browser-verification.md` — 浏览器调试闭环（Python 验证入口）
