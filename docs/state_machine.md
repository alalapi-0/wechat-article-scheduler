# 草稿排期状态机

Status: Documentation-backed target states

当前数据库主表 `publish_jobs.status` 仍以 `pending`、`running`、`done`、`failed`、`cancelled`、`waiting_confirmation` 等轻量状态为主。本文件补充 External Agent Assist Mode 的目标状态语义，不在本轮强制迁移数据库。

## External Agent Assist 状态

- `draft_created`：微信公众号 API 草稿已创建，本地排期目标已达成。
- `external_agent_task_ready`：外部 Agent 任务包已生成。
- `external_agent_in_progress`：用户或外部 Agent 正在处理。
- `external_agent_checked`：外部 Agent 已完成检查。
- `manual_confirmation_required`：等待用户确认草稿检查或后台人工处理结果。
- `proof_attached`：用户已回填证明。
- `completed_without_publish`：草稿创建与检查完成，不执行发布。
- `published`：仅保留为历史/人工 proof 状态；不能由 Agent 自动设置。
- `failed`：任务失败。

## 状态规则

- `external_agent_task_ready` 只能由任务包导出产生。
- `external_agent_checked` 不能等价于已发布。
- `manual_confirmation_required` 之后必须由用户处理。
- `proof_attached` 之前不能标记为完成。
- `completed_without_publish` 表示草稿检查完成，不代表正式发布。
- `published` 只能在用户明确确认并提交 proof 后设置；当前项目不通过 API/Agent 自动设置。

## 当前实现映射

- API 草稿创建后，现有 scheduler 会把草稿创建任务记为 `done` 并写入 `draft_created` 事件；这不代表已发布。
- `export-agent-task` 会写入 `external_agent_task_ready` 事件和 outbox 任务包。
- proof 回填继续复用现有 `publish_proofs` 机制；更细状态迁移留给后续完善轮。

