# Codex Handoff

> 模板：由 Cursor 在交接 Codex 前填写。勿包含密钥。

## Repo

wechat-article-scheduler — Python CLI + FastAPI 微信公众号草稿箱辅助工作台

## Current branch

main

## Current goal

（填写本轮目标，一句话）

## Must read

- AGENTS.md
- agent_layer.yaml
- agent_tools.yaml
- docs/TOOL_USAGE_POLICY.md
- docs/AGENT_RUNBOOK.md
- reports/latest-agent-report.json
- governance/round_state.yaml

## Current P0/P1

- P0: （列表或「无」）
- P1: （列表或「无」）

## Latest gate result

- `reports/gate_result.json` status:
- `python scripts/agent_gate.py gate` exit code:

## Relevant files

（列出 3–10 个路径）

## Do not touch

- `.env`
- `articles/imported/` 用户文稿（无授权勿删）
- 真实发布流程

## Tools expected

- shell, pytest
- （若需）playwright MCP, context7

## Commands to run

```bash
python scripts/tool_probe.py
python scripts/agent_layer_gate.py
python -m pytest tests/<relevant>.py
```

## Acceptance criteria

- [ ] gate passed
- [ ] 报告已更新
- [ ] 无 P0/P1 引入

## Return format

JSON 报告写入 `reports/latest-agent-report.json`，并说明 changed_files、risks、next_recommended_round。
