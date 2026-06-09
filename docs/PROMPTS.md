# Prompt Templates — Tool-aware Agent Layer 2.0

每模板均要求：先读 AGENTS.md、agent_tools.yaml、latest-agent-report → 判断搜索 → 选工具 → 小任务 → gate → report → 不 push → 不 real API。

---

## 1. Cursor 工具盘点轮

```
你是 wechat-article-scheduler 的 Tool-aware Agent。
先读：AGENTS.md, agent_layer.yaml, agent_tools.yaml, reports/latest-agent-report.json
运行：python scripts/tool_probe.py
更新：docs/TOOL_INVENTORY.md, agent_tools.yaml, reports/tool_probe_report.json
判断每个 MCP 的 configured vs callable_now（当前线程工具列表）。
本轮只做工具盘点，不改业务代码。
运行：python scripts/agent_layer_gate.py
生成：reports/latest-agent-report.json（mode: tool-probe）
禁止：real API, real publish, push, 读取 .env
```

## 2. Cursor 小步实现轮

```
先读 AGENTS.md + agent_tools.yaml + reports/latest-agent-report.json
本轮目标：（填写一个 layer2-0xx 或 docs/rounds.md 单任务）
scope：最多 3 个文件
工具：优先 repo search + shell pytest
若涉及 UI：必须 playwright 或 chrome-devtools
gate：python scripts/agent_layer_gate.py && python scripts/agent_gate.py gate
报告：latest-agent-report.json，记录 tools_used/tools_not_used
禁止：real publish, 自动 push
```

## 3. Cursor 用户视角测试轮

```
先读 docs/USER_VIEW_TESTING.md
启动：python -m wechat_article_scheduler.cli serve
用 playwright/chrome-devtools 验证 http://127.0.0.1:8080/ 主流程
截图 + console + network
运行：python scripts/user_view_test.py --pytest（若安全）
gate + report
禁止：微信后台最终发布点击
```

## 4. Cursor P0/P1 修复轮

```
先读 reports/latest-agent-report.json 的 severity_summary
只修 P0/P1；不做 P2/P3 优化
修复后：python -m pytest <相关测试>
gate + 更新 severity_summary
```

## 5. Codex 高价值 handoff Prompt

```
读取 docs/CODEX_HANDOFF.md（已由 Cursor 填写）
遵守 AGENTS.md 与 docs/CODEX_USAGE.md
单轮小 scope；no real API；no real publish
运行 gate；返回 JSON 报告格式见 schemas/agent_round_report.schema.json
```

## 6. Codex Review Prompt

```
Review 分支 diff（不 push）
先读 AGENTS.md, docs/AGENT_SAFETY.md
关注：密钥泄露、real publish 路径、测试删除
输出：severity P0-P3 列表 + 建议
```

## 7. Web Research Prompt

```
先读 docs/SEARCH_POLICY.md
搜索官方文档：（填写 query）
写入 docs/RESEARCH_NOTES.md（日期、来源、不确定性）
若无法搜索：记录 TOOL_UNAVAILABLE_WEB_SEARCH
```

## 8. MCP Probe Prompt

```
先读 docs/runbooks/cursor_mcp_runbook.md
运行 npm run check:mcp
在当前线程尝试最小只读 MCP 调用（不修改外部数据）
更新 reports/tool_probe_report.json 的 callable_now
若线程无 MCP：BLOCKED: MISSING_FROM_THREAD_TOOL_REGISTRY
```
