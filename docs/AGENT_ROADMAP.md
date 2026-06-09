# Agent Roadmap — Tool-aware Incremental (Layer 2.0)

> 与 `docs/rounds.md`（功能 round_000+）并行。本路线图专注**工具感知、门禁、验证、交接**。  
> 每轮：小 scope → 指定工具 → gate → report。

---

## Phase 0 — 仓库事实层

### layer2-001 — 工具探针基线
- **goal**: 建立 tool_probe 与 TOOL_INVENTORY
- **why_now**: Agent 进入仓库需知道环境
- **scope**: scripts/tool_probe.py, docs/TOOL_INVENTORY.md
- **likely_files**: agent_tools.yaml, reports/tool_probe_report.json
- **tools_to_use**: shell
- **tools_to_probe**: git, node, python, pytest, playwright
- **web_search_needed**: false
- **commands_to_run**: `python scripts/tool_probe.py`
- **acceptance_criteria**: tool_probe_report.json 存在且 probes ≥10
- **risks**: 环境差异
- **fallback**: 记录 BLOCKED_ENV
- **depends_on**: —

### layer2-002 — agent_layer.yaml 机器配置
- **goal**: 统一 read_first 与 commands
- **scope**: agent_layer.yaml
- **tools_to_use**: Read, Write
- **commands_to_run**: `pytest tests/test_agent_layer_gate.py`
- **acceptance_criteria**: version=2, commands 非空
- **depends_on**: layer2-001

### layer2-003 — 既有治理对齐审计
- **goal**: 文档化 agent_gate.py 与 Layer2 关系
- **scope**: docs/AGENT_LAYER_AUDIT.md
- **tools_to_use**: Grep, Read
- **web_search_needed**: false
- **acceptance_criteria**: 审计表完整
- **depends_on**: layer2-002

---

## Phase 1 — 工具盘点层

### layer2-004 — MCP 线程注册表检查
- **goal**: 记录 callable_now per MCP
- **scope**: docs/TOOL_INVENTORY.md, reports/tool_probe_report.json
- **tools_to_probe**: chrome-devtools, playwright, wechat-chrome-session, context7, github, stitch
- **commands_to_run**: `npm run check:mcp`, `npm run check:cursor-mcp`
- **acceptance_criteria**: 每个 MCP 有 configured/callable_now/fallback
- **risks**: 线程无 MCP → BLOCKED
- **fallback**: pytest e2e
- **depends_on**: layer2-001

### layer2-005 — agent_tools.yaml 细化
- **goal**: 工具→任务映射入库
- **scope**: agent_tools.yaml
- **acceptance_criteria**: policies 段完整
- **depends_on**: layer2-004

### layer2-006 — 工具使用策略
- **goal**: docs/TOOL_USAGE_POLICY.md 落地
- **tools_to_use**: Write
- **acceptance_criteria**: 10 节问答齐全
- **depends_on**: layer2-005

---

## Phase 2 — 搜索与文档更新层

### layer2-007 — Cursor 官方能力同步
- **goal**: RESEARCH_NOTES Query Cursor
- **web_search_needed**: true
- **tools_to_use**: web_search
- **acceptance_criteria**: RESEARCH_NOTES 有官方来源
- **depends_on**: layer2-006

### layer2-008 — Codex 官方能力同步
- **goal**: RESEARCH_NOTES Query Codex + CODEX_USAGE
- **web_search_needed**: true
- **depends_on**: layer2-007

### layer2-009 — 微信 API 规则同步
- **goal**: digest/title/content 限制写入 RESEARCH_NOTES
- **web_search_needed**: true
- **likely_files**: docs/wechat_capability_matrix.md
- **depends_on**: layer2-008

### layer2-010 — SEARCH_POLICY 固化
- **goal**: 必须搜索场景清单
- **scope**: docs/SEARCH_POLICY.md
- **depends_on**: layer2-009

---

## Phase 3 — Agent 规则层

### layer2-011 — AGENTS.md Layer2 补强
- **goal**: Read First + Round Lifecycle
- **scope**: AGENTS.md
- **depends_on**: layer2-010

### layer2-012 — Cursor rules 五件套
- **goal**: agent-layer, tool-usage, search-policy, safety-gates, user-view-testing
- **scope**: .cursor/rules/
- **depends_on**: layer2-011

### layer2-013 — Codex handoff 模板演练
- **goal**: 填写一份示例 CODEX_HANDOFF（无密钥）
- **scope**: docs/CODEX_HANDOFF.md
- **depends_on**: layer2-012

---

## Phase 4 — 门禁脚本层

### layer2-014 — agent_layer_gate 首版
- **goal**: gate_result.json 输出
- **commands_to_run**: `python scripts/agent_layer_gate.py`
- **depends_on**: layer2-013

### layer2-015 — gate 测试固化
- **goal**: tests/test_agent_layer_gate.py
- **depends_on**: layer2-014

### layer2-016 — 与 agent_gate.py 双 gate 文档
- **goal**: AGENT_RUNBOOK 说明双 gate
- **depends_on**: layer2-015

---

## Phase 5 — 报告与审计层

### layer2-017 — report schema
- **goal**: schemas/agent_round_report.schema.json
- **depends_on**: layer2-016

### layer2-018 — latest-agent-report 首轮
- **goal**: reports/latest-agent-report.json
- **depends_on**: layer2-017

### layer2-019 — audit log 追加机制
- **goal**: reports/agent_audit_log.jsonl
- **depends_on**: layer2-018

### layer2-020 — AGENT_REPORTING 文档
- **depends_on**: layer2-019

---

## Phase 6 — 用户视角测试层

### layer2-021 — user_view_test 脚本
- **goal**: scripts/user_view_test.py
- **commands_to_run**: `python scripts/user_view_test.py --dry-run`
- **tools_to_use**: shell
- **depends_on**: layer2-020

### layer2-022 — Web 工作台 smoke（MCP）
- **goal**: 本地 serve + playwright 截图
- **tools_to_use**: playwright 或 chrome-devtools
- **tools_to_probe**: playwright
- **acceptance_criteria**: 截图入 docs/reports/ui_review/
- **risks**: MCP 不可用 → pytest fallback
- **depends_on**: layer2-021

### layer2-023 — 空状态/seeded 回归
- **goal**: 复验 empty_state + seeded viewport
- **likely_files**: tests/test_user_view_rounds_abcd.py
- **depends_on**: layer2-022

### layer2-024 — USER_VIEW_TESTING 文档完善
- **depends_on**: layer2-023

---

## Phase 7 — 核心功能稳定层

### layer2-025 — scan/plan mock 闭环探针
- **goal**: CLI dry-run 无联网
- **commands_to_run**: `python -m wechat_article_scheduler.cli scan`, `plan`
- **depends_on**: layer2-024

### layer2-026 — Web 队列/预检用户路径
- **goal**: 普通用户视图验收
- **tools_to_use**: browser MCP
- **depends_on**: layer2-025

### layer2-027 — external agent 任务包格式检查
- **goal**: export-agent-task dry-run
- **likely_files**: tests/test_external_agent_task_package.py
- **depends_on**: layer2-026

---

## Phase 8 — P0/P1 自动修复闭环

### layer2-028 — P0/P1 清单从 round_state 同步
- **goal**: latest-agent-report severity_summary
- **likely_files**: governance/round_state.yaml
- **depends_on**: layer2-027

### layer2-029 — 失败测试分级
- **goal**: 仅修 P0/P1 相关测试
- **commands_to_run**: `python -m pytest -q`
- **depends_on**: layer2-028

---

## Phase 9 — UI/UX 产物质量

### layer2-030 — Desktop-first 工作台审查
- **goal**: 1280px 布局 + 高级信息开关
- **tools_to_use**: playwright, stitch（可选）
- **depends_on**: layer2-029

---

## Phase 10 — mock / dry-run / real API 分离

### layer2-031 — real_api_check dry-run 门禁
- **commands_to_run**: `python scripts/real_api_check.py --dry-run --skip-if-blocked`
- **depends_on**: layer2-030

### layer2-032 — 发布误触防护审计
- **goal**: 确认无自动 publish 路径
- **likely_files**: src/wechat_article_scheduler/publish_config.py
- **depends_on**: layer2-031

---

## Phase 11 — 成本控制

### layer2-033 — COST_CONTROL 与 ledger 路径验证
- **scope**: docs/COST_CONTROL.md, reports/real_api_runs/
- **depends_on**: layer2-032

---

## Phase 12 — Codex handoff

### layer2-034 — 首次 Codex handoff 演练（mock）
- **goal**: 填写 CODEX_HANDOFF 并审查
- **depends_on**: layer2-033

---

## Phase 13 — Cursor 主力小轮次

### layer2-035 — PROMPTS.md 八模板落地
- **depends_on**: layer2-034

### layer2-036 — 下一轮功能 round 与 Layer2 绑定
- **goal**: 在 latest-agent-report 中链接 docs/rounds.md 当前 round
- **depends_on**: layer2-035

---

## Phase 14 — 多 Agent 可选层

### layer2-037 — Cloud Agent AGENTS.md 验证清单
- **web_search_needed**: true
- **depends_on**: layer2-036

### layer2-038 — CI 接入 agent_layer_gate（可选）
- **goal**: 文档化 CI 步骤，不强制改 CI
- **depends_on**: layer2-037

---

## Phase 15 — 长期维护

### layer2-039 — 季度工具探针复跑 SOP
- **commands_to_run**: `python scripts/tool_probe.py`
- **depends_on**: layer2-038

### layer2-040 — Layer2 与 rounds.md 同步检查
- **goal**: 审计 docs/AGENT_LAYER_AUDIT.md 更新
- **depends_on**: layer2-039

---

## 微信公众号专项（贯穿）

- **平台规则搜索**: layer2-009, layer2-032
- **dry-run / 草稿模式**: layer2-025, layer2-031
- **浏览器接管**: layer2-004, layer2-022
- **失败恢复**: layer2-029
- **定时发布验证**: 仅浏览器/人工；API 不能写入微信后台时间
