# Stitch MCP 配置

## 当前方案

本仓库使用 Remote MCP，不安装本地 proxy：

```json
{
  "mcpServers": {
    "stitch": {
      "url": "https://stitch.googleapis.com/mcp",
      "headers": {
        "X-Goog-Api-Key": "${env:STITCH_API_KEY}"
      }
    }
  }
}
```

Cursor 支持在 `headers` 中解析 `${env:NAME}`，因此无需把 key 写入仓库。Stitch SDK 的默认 MCP endpoint 也是 `https://stitch.googleapis.com/mcp`。

## 设置 Key

从 Stitch Settings 的 API Keys 页面创建 key，然后只在本机设置：

```bash
export STITCH_API_KEY="your-local-key"
```

`.env.example` 只有占位符。不要提交 `.env`，不要把 key 写进 `.cursor/mcp.json`、脚本、文档、截图或日志。若 Cursor 从图形界面启动后读取不到 shell 环境，请在启动 Cursor 的进程环境中设置变量，再重新打开工作区。

## 加载与验证

1. 运行 `npm run check:mcp`。
2. 运行 `npm run check:stitch`。
3. 重启 Cursor 或 Reload Window。
4. 打开 Cursor Settings -> Tools & MCP。
5. 确认 `stitch` 已启用且没有认证错误。
6. 让 Agent 列出 Stitch tools 或项目；不要在验证阶段生成大批页面。

静态检查通过不等于远端认证成功。当前环境没有 key 时，只能确认 JSON、endpoint、环境变量占位符和目录结构。

## 故障排查

- `STITCH_API_KEY` 缺失：在 Cursor 进程环境设置变量后重载。
- 认证失败：重新创建或检查 key 权限；不要把 key 粘贴进 issue 或日志。
- MCP 不显示：确认 `.cursor/mcp.json` JSON 有效并重启 Cursor。
- 网络或配额错误：记录错误摘要，继续使用文档模板，不伪装成 Stitch 已成功。

只有旧版 Cursor 无法在 Remote MCP header 中解析环境变量时，才考虑 `@google/stitch-sdk` 的 `StitchProxy` stdio 方案；引入前应单独评审依赖和安全边界。
