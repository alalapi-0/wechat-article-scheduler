# Tool Usage Policy

Date: 2026-06-09  
Applies to: Cursor（主力）、Codex（辅助）、本地脚本

## 1. 任务 → 工具映射（必须）

| 任务阶段 | 必须工具 | 说明 |
|----------|----------|------|
| 进入仓库 | Read | `AGENTS.md` → `agent_layer.yaml` → `agent_tools.yaml` → `reports/latest-agent-report.json` |
| 工具规划前 | tool_probe | `python scripts/tool_probe.py` 或读取 `reports/tool_probe_report.json` |
| 代码理解 | Grep / SemanticSearch / Read | 优先仓库内搜索 |
| 最新官方文档 | WebSearch 或 context7 | 见 `docs/SEARCH_POLICY.md` |
| 确定性验证 | shell + pytest | `python scripts/agent_layer_gate.py` + `python scripts/agent_gate.py gate` |
| 本地 Web UI | chrome-devtools 或 playwright | `http://127.0.0.1:8080/` |
| 微信已登录后台 | wechat-chrome-session | 禁止 playwright isolated 冒充 |
| 外部仓库/issue | gh 或 github MCP | push 需人工授权 |
| 报告 | Write JSON | `reports/latest-agent-report.json` |

## 2. 优先工具

- **小步修复**：Cursor Agent + shell
- **UI 验证**：playwright MCP > chrome-devtools > pytest e2e
- **库 API 不确定**：context7 > web_search > 用户提供的文档
- **长程重构**：Codex handoff（`docs/CODEX_HANDOFF.md`）
- **门禁**：`scripts/agent_layer_gate.py`（Layer 2）+ `scripts/agent_gate.py gate`（既有 round 治理）

## 3. 禁止工具场景

| 禁止 | 原因 |
|------|------|
| 默认 `WECHAT_MODE=real` 联网 | 付费/真实 API |
| MCP 点击最终发布 | 真实发布 |
| 打印 `.env` / token / cookie | 密钥泄露 |
| `git push --force` main | 破坏性 |
| Multitask 子 Agent 操作微信后台 | MCP 未注册到子线程 |
| 为通过 gate 删除失败测试 | 虚假通过 |

## 4. Fallback

| 工具不可用 | Fallback |
|------------|----------|
| playwright MCP | `pytest tests/test_ui_e2e.py` + `scripts/user_view_test.py` |
| wechat-chrome-session | `export-agent-task` 外部任务包 + 人工 |
| context7 | WebSearch 官方文档 |
| github MCP | `gh` CLI |
| web_search | 记录 `TOOL_UNAVAILABLE_WEB_SEARCH`；请用户提供文档 |
| Codex | Cursor 小轮次继续 |

## 5. Cursor vs Codex 分工

| Cursor | Codex |
|--------|-------|
| 本地快速修复 | 大范围重构 |
| UI / 浏览器调试 | 长程实现 |
| MCP 联动 | 代码审查 / PR review |
| 文档与规则落地 | worktree 并行 |
| 每轮小 scope | 高价值 handoff 任务 |

## 6. MCP「配置了但不用」防控

每轮报告必须包含 `tools_used` 与 `tools_not_used`。若 MCP 可用但未使用，必须在 `tools_not_used` 写明原因。UI/发布相关轮次 **必须** 尝试 browser 类 MCP。

## 7. Web 搜索防过期

- 优先官方文档、changelog、GitHub release
- 社区博客仅辅助
- 写入 `docs/RESEARCH_NOTES.md` 并标注不确定性
- 不把搜索结果当平台合规依据

## 8. 用户视角测试

1. `python -m wechat_article_scheduler.cli serve`
2. 打开 `http://127.0.0.1:8080/`
3. 完成主流程：上传/扫描 → 排期 → 队列 → 预检
4. console + network + 截图
5. `python scripts/user_view_test.py --pytest`（非 dry-run 时）

## 9. 真实 API / 发布防误触

- 默认 `WECHAT_MODE=mock`
- `scripts/real_api_check.py` 必须 `--dry-run` 或显式 `WECHAT_MODE=real`
- `WECHAT_ENABLE_PUBLISH=false` 为草稿-only 语义
- 浏览器任务停在人类确认前

## 10. 工具使用记录

每轮结束更新 `reports/latest-agent-report.json` 的 `tools_used` / `tools_not_used`，并追加 `reports/agent_audit_log.jsonl`。
