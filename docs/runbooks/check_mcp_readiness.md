# MCP Readiness 检查清单

可复制本清单到 Agent 报告或 round 记录中。完整说明见 [`cursor_mcp_runbook.md`](cursor_mcp_runbook.md)。

**不运行额外脚本**；仅引用已有检查命令。

---

## A. 配置层（仓库根目录）

```bash
node scripts/check_mcp_config.js
npm run check:stitch
```

- [ ] `check_mcp_config.js` → PASS（7 server 已声明）
- [ ] `check:stitch` → PASS

## B. 当前线程（必须在对话内探测）

- [ ] 普通前台 Agent（非 Multitask）
- [ ] chrome-devtools：`list_pages` → 至少 1 页（如 `about:blank`）
- [ ] playwright：`browser_tabs` list → 至少 1 tab
- [ ] context7：`resolve-library-id`（FastAPI）→ 有库 ID
- [ ] filesystem：`list_allowed_directories` → 仓库根路径
- [ ] github：`search_repositories` → 找到本仓库
- [ ] stitch：`list_projects` → 有项目列表

## C. 浏览器上下文（按任务类型）

**本地 Web UI**（`http://127.0.0.1:8080/`）：

- [ ] 使用 chrome-devtools 或 playwright（isolated 可接受）
- [ ] 未把 isolated browser 当作已登录公众号

**微信公众号后台**（`mp.weixin.qq.com`）：

- [ ] 使用 wechat-chrome-session（或用户批准的 CDP）
- [ ] `list_pages` 含已登录标签（非仅 `about:blank`）
- [ ] 无扫码/验证码阻塞，或已停止等待用户

## D. 安全

- [ ] 未输出 token / cookie / API Key
- [ ] 未把 profile 或 cookie 写入仓库
- [ ] 未自动点击最终发布

## E. 结果

- [ ] 全部通过 → 可继续任务
- [ ] 线程无工具 → `BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY`
- [ ] 公众号需登录 → 按 [`mcp_troubleshooting.md`](mcp_troubleshooting.md) §7

---

**基线参考日期**：2026-06-07
