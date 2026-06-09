# Agent Reporting

## 报告文件

| 文件 | 用途 |
|------|------|
| `reports/latest-agent-report.json` | 下一轮 Agent 必读最新状态 |
| `reports/agent_audit_log.jsonl` | 历史审计追加日志 |
| `reports/gate_result.json` | `agent_layer_gate.py` 输出 |
| `reports/tool_probe_report.json` | 工具探针 |
| `schemas/agent_round_report.schema.json` | JSON Schema |

## 必填字段

见 schema；尤其：

- `tools_used` / `tools_not_used`
- `web_research`
- `severity_summary`（p0–p3）
- `gate_status`
- `next_recommended_round`

## 追加审计

```bash
# 每轮结束后由 Agent 追加一行 JSON（勿删历史）
echo '{"round_id":"layer2-001",...}' >> reports/agent_audit_log.jsonl
```

## 与既有报告的关系

- `docs/reports/agent_gate_report.md` — 既有 gate 人类可读报告
- `docs/reports/ux_loop/` — 用户视角测试报告
- Layer 2.0 JSON 报告与之互补，供机器读取
