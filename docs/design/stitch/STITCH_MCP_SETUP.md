# Stitch MCP 配置

## 两种配置方式

| 方式 | 说明 | 本项目 |
|------|------|--------|
| **Remote MCP** | 在 `.cursor/mcp.json` 中直接配置 `url: https://stitch.googleapis.com/mcp` + `X-Goog-Api-Key` header | 已弃用（Cursor 对 remote stitch 常出现未加载 / 0 tools） |
| **Local stdio proxy** | 本地 `scripts/stitch_mcp_proxy.mjs`，经 `@google/stitch-sdk` 的 `StitchProxy` 转发到官方 endpoint | **当前默认** |

本项目最终使用 **Local stdio proxy**，server 名称仍为 `stitch`。

## 当前 `.cursor/mcp.json` 片段

```json
{
  "mcpServers": {
    "stitch": {
      "type": "stdio",
      "command": "node",
      "args": ["scripts/stitch_mcp_proxy.mjs"],
      "env": {
        "STITCH_API_KEY": "${env:STITCH_API_KEY}"
      }
    }
  }
}
```

proxy 从环境变量读取 `STITCH_API_KEY`，不打印 key；缺失时 stderr 报错并退出。

## 设置 Key

1. 打开 [Stitch Settings → API Keys](https://stitch.withgoogle.com/) 创建 key。
2. 只在本机设置，**不要**写入仓库：

```bash
export STITCH_API_KEY="your-local-key"
```

或在项目根 `.env` 中设置（`.env` 已在 `.gitignore` 中）。`.env.example` 只有占位符。

**注意：** 若 Cursor 从 Dock/Finder 启动，可能读不到 shell 的 `export`。请在 Cursor 能访问的环境设置变量，或在本机 shell profile / launchd 中注入后再启动 Cursor。

### OAuth 说明（非本项目默认路径）

Google 官方 MCP endpoint 在部分客户端上也可通过 **gcloud OAuth**（`@_davideast/stitch-mcp proxy` + `GOOGLE_CLOUD_PROJECT`）认证。该路径需要 `gcloud auth application-default login` 与启用 `stitch.googleapis.com` MCP API。本项目 **不** 采用 OAuth proxy，以避免与现有 `STITCH_API_KEY` 工作流冲突；若 API Key 路径不可用，再单独评估 OAuth 方案。

## 加载与验证

### 1. 静态检查

```bash
npm install          # 安装 @google/stitch-sdk（proxy 依赖）
npm run check:mcp
npm run check:stitch
```

### 2. Cursor 运行时验证（必需）

修改 `.cursor/mcp.json` 后 **必须完全退出 Cursor**（Cmd+Q），再重新打开本仓库：

1. Settings → Tools & MCP → 确认 `stitch` **Enabled**，且无认证错误。
2. **新建普通前台 Agent 对话**（禁用 Multitask）。
3. 运行：

```bash
cursor-agent mcp list
cursor-agent mcp list-tools stitch
```

**验收标准：** `list-tools stitch` 返回真实 tools（非空）。若显示 `No tools/prompts/resources` 或 `needs approval` / `has not been approved`，**不能**判定 Stitch 可用。

### 3. 当前 Agent 线程

CLI 层 ready 不等于当前对话已注册工具。必须在 **新开的普通前台 Agent** 中确认 stitch 原生工具可见；否则见 [`docs/cursor_tool_registry_check.md`](../../cursor_tool_registry_check.md)。

## 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `STITCH_API_KEY 未设置` | Cursor 进程无 key | 设置环境变量后 Cmd+Q 重启 Cursor |
| `needs approval` / `has not been approved` | Settings 未批准 stitch | Tools & MCP 批准 → 完全重启 → 新对话 |
| `MCP server does not exist: stitch` | 旧对话工具注册表 | 完全重启 Cursor，新建普通前台 Agent |
| `list-tools` 成功但 tools 为空 | 认证失败或 transport 不兼容 | 检查 key；确认使用 stdio proxy 而非 remote |
| Remote 配置 API Key 报 OAuth 错误 | 官方 endpoint 在该 transport 下不接受 API Key | 改用 stdio proxy（当前默认） |

## Fallback

Stitch 不可用时，UI 设计任务继续使用 `docs/design/stitch/` 模板；页面验收使用 **chrome-devtools** 或 **playwright**，不得假装 Stitch 已生成设计。

## 参考

- [@google/stitch-sdk StitchProxy](https://github.com/google-labs-code/stitch-sdk)
- [`docs/mcp/WORKSPACE_MCP_SERVERS.md`](../../mcp/WORKSPACE_MCP_SERVERS.md)
- [`docs/cursor_tool_registry_check.md`](../../cursor_tool_registry_check.md)
