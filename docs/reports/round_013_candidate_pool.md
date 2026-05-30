# Round 13+ 候选池（Round 12 规划）

> 机器轮次仍以 `docs/rounds.md` 与 `scripts/agent_gate.py` 为准；本文件供 Agent 挑选下一小步任务。

## 近期优先（Phase 4）

| 候选 | 说明 | 依赖 |
|---|---|---|
| Renderer 规则矩阵 | 补 `docs/renderer_rules.md` 与 fixture | Round 13 |
| 封面索引 smoke | 新增 `tests/test_cover_assets.py` | Round 14 |
| 内容库查询 | 合集/标签筛选与 `test_content_library.py` | Round 15 |

## 中期（Phase 5–6）

| 候选 | 说明 |
|---|---|
| Scheduler 人工闸门 | 未批准任务阻断 real 路径 |
| 真实发布试运行手册 | WECHAT_ENABLE_PUBLISH 显式开关文档化 |
| 普通用户术语映射 | 展示层中文化，不改 DB 字段名 |
| Playwright ui_review | Round 19 视觉基线 |

## 暂不做

- React/Vue 控制台
- 默认真实发布、cookie 持久化
- 商业化多用户后台

## 使用方式

1. 完成当前 `governance/round_state.yaml` 中的 `acceptance_criteria`
2. `python scripts/agent_gate.py gate`
3. 需要新 Round 39+ 时：先改 `docs/rounds.md`，再同步 `ROUND_ORDER` / `tests/test_agent_gate.py`
