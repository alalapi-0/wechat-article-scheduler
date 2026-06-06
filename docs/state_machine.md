# 发布状态机

Status: Documentation-backed target states

当前数据库主表 `publish_jobs.status` 仍以 `pending`、`running`、`done`、`failed`、`cancelled`、`waiting_confirmation` 等轻量状态为主。本文件补充 External Agent Assist Mode 的目标状态语义，不在本轮强制迁移数据库。

## External Agent Assist 状态

- `draft_created`：微信公众号 API 草稿已创建。
- `external_agent_task_ready`：外部 Agent 任务包已生成。
- `external_agent_in_progress`：用户或外部 Agent 正在处理。
- `external_agent_checked`：外部 Agent 已完成检查。
- `manual_confirmation_required`：等待用户确认。
- `proof_attached`：用户已回填证明。
- `completed_without_publish`：只完成草稿检查，不执行发布。
- `published`：真实发布完成，或用户明确确认已发布并提交 proof。
- `failed`：任务失败。

## 状态规则

- `external_agent_task_ready` 只能由任务包导出产生。
- `external_agent_checked` 不能等价于已发布。
- `manual_confirmation_required` 之后必须由用户处理。
- `proof_attached` 之前不能标记为完成。
- `completed_without_publish` 表示草稿检查完成，不代表正式发布。
- `published` 只能在真实发布完成或用户明确确认后设置。

## 当前实现映射

- API 草稿创建后，现有 scheduler 仍可能把 draft-only job 记为 `done` 并写入 `draft_created` 事件。
- `export-agent-task` 会写入 `external_agent_task_ready` 事件和 outbox 任务包。
- proof 回填继续复用现有 `publish_proofs` 机制；更细状态迁移留给后续完善轮。

