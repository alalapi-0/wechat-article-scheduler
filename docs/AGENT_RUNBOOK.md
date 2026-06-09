# Agent Runbook — Tool-aware Layer 2.0

Date: 2026-06-09

## 每轮标准流程

```
1. 读取 AGENTS.md + agent_layer.yaml + agent_tools.yaml + reports/latest-agent-report.json
2. python scripts/tool_probe.py（或读 reports/tool_probe_report.json）
3. 判断是否需要 Web 搜索 → docs/SEARCH_POLICY.md
4. 选定本轮工具（写入计划）
5. 小 scope 实现（仅一个主要能力）
6. python scripts/agent_layer_gate.py
7. python scripts/agent_gate.py gate（既有 round 治理，可选但推荐）
8. 生成 reports/latest-agent-report.json + 追加 agent_audit_log.jsonl
```

## 启动与验证

```bash
# 安装
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && npm install

# 初始化
cp .env.example .env   # 勿提交；Agent 禁止读取打印密钥
cp config/rules.example.yaml config/rules.yaml
python -m wechat_article_scheduler.cli init-db

# 开发
python -m wechat_article_scheduler.cli serve   # http://127.0.0.1:8080/

# 测试
python -m pytest
python scripts/user_view_test.py --dry-run
python scripts/agent_layer_gate.py
python scripts/agent_gate.py status
python scripts/agent_gate.py gate
```

## MCP Readiness（任务开始前）

先读 `docs/runbooks/cursor_mcp_runbook.md`，再：

```bash
npm run check:mcp
npm run check:stitch   # 设计任务时
```

## 与既有治理的关系

| Layer | 文件 | 用途 |
|-------|------|------|
| 既有 Round 治理 | `docs/rounds.md`, `scripts/agent_gate.py` | round_000+ 功能推进 |
| Layer 2.0 | `docs/AGENT_ROADMAP.md`, `agent_layer.yaml` | 工具感知 + 门禁 + 报告 |

两者并行：Layer 2.0 不替代 `docs/rounds.md`，而是让 Agent 知道**用什么工具、如何验证、如何交接**。

## 退出码

- `agent_layer_gate.py`: 0=passed, 1=failed/blocked
- `agent_gate.py`: 0=PASS, 1=WARNING, 2=BLOCKED

## 人工决策点

- 真实 API（`WECHAT_MODE=real`）
- 真实公众号后台发布点击
- git commit / push
- 删除 `articles/` 用户文稿
