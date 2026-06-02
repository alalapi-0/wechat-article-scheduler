# 可选正式发布（Round 20）

Status: Current

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `WECHAT_MODE` | `mock` | `mock` 不联网；`real` 调用真实微信 API |
| `WECHAT_ENABLE_PUBLISH` | `false` | `real` 模式下为 `false` 时**全局草稿-only**，不调用 `freepublish/submit` |

## 任务级 `publish_action`

写入 `publish_jobs.publish_config_json`：

- `draft` — 仅创建/更新草稿，不提交发布（即使全局开关打开）
- `publish` — 意图正式发布；仅当 `WECHAT_MODE=real` 且 `WECHAT_ENABLE_PUBLISH=true` 时才会 `freepublish/submit`

## 工作台

- 顶部安全条：`/api/status` → `publish_policy`
- 发布前预检：`/api/publish-preflight` 含待发布任务分布
- 队列列「发布配置」含有效行为徽章（`publish_effective_badge`）
- 真实发布 + 开关打开：执行到点前 **二次确认** + 预检阻断

## 代码

- `publish_policy.py` — 策略解析
- `publish_config.should_submit_publish()` — 是否提交发布
- `scheduler/domain.py` — 执行与 `publish_skipped_draft_only` 事件
