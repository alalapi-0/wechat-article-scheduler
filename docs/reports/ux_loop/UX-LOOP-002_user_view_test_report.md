# UX-LOOP-002 用户视角测试报告

## 1. 本轮结论

- 是否存在 P0：否
- 是否存在 P1：是（发现 1 项，已修复）
- 是否需要自动修复：是
- 是否允许停止循环：是（修复后无剩余 P0/P1）
- 当前最高问题等级：P2
- 本轮是否已使用浏览器工具：是
- 本轮是否已检查 UI 美观性：是

## 2. 测试环境

- 操作系统：darwin 25.3.0
- Python 版本：3.14.5
- 启动命令：修复后回归 `DATABASE_PATH=/tmp/wcas-ux-loop2.sqlite3 .venv/bin/python -m wechat_article_scheduler.cli serve --port 8082`
- WECHAT_MODE：mock
- WECHAT_ENABLE_PUBLISH：false
- 使用的 MCP 工具：Playwright、filesystem

## 3. 实际测试路径

1. push UX-LOOP-001 后重新打开首页与详情；
2. 验证 `/api/status` publish_policy effective/ignored；
3. 验证详情页 done 任务下一步文案；
4. CLI `export-agent-task` 检查任务包文件齐全；
5. 发现首页在草稿已创建后仍提示「待生成排期」；
6. 修复 chain summary + workbench hints；
7. 全量 pytest + agent_gate。

## 4. 功能通过情况总览

| 模块 | 是否通过 | 问题等级 | 说明 |
|---|---|---|---|
| 首页 Dashboard | 部分→已修 | P1→已修 | 草稿完成后误提示 plan |
| 文章详情 | 是 | — | UX-LOOP-001 修复生效 |
| 外部 Agent 任务包 | 是 | — | task.json 等 7 文件齐全 |
| 其余主流程 | 是 | — | 与 LOOP-001 一致 |

## 6. 问题清单

### P1-007

- 等级：P1
- 模块：首页 / 链路摘要
- 类型：UX
- 问题描述：草稿已创建（schedule_state=remote_draft_ready）后，首页仍显示「有 N 篇已导入，待生成草稿创建计划」
- 复现：run-once 成功后刷新首页
- 修复：`wechat_chain_summary` 排除非 imported schedule_state；`workbench_mvp` 增加「流程已走完」分支
- 是否必须本轮修复：是

## 10. 本轮是否进入修复

- 是否进入修复：是
- 修复后测试：460 passed，agent_gate PASS

## 11. 下一轮

循环停止：剩余均为 P2/P3/P4。
