# 历史可选正式发布策略（已降级）

Status: Historical — 当前目标只做按时创建草稿

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `WECHAT_MODE` | `mock` | `mock` 不联网；`real` 调用真实微信 API |
| `WECHAT_ENABLE_PUBLISH` | `false` | 历史开关；当前调度策略不应调用 `freepublish/submit` |

## 任务级 `publish_action`

写入 `publish_jobs.publish_config_json`：

- `draft` — 仅创建/更新草稿，不提交发布
- `publish` — 历史值；当前解释为“创建草稿后需要用户人工后台发布”，不会触发 `freepublish/submit`

## 工作台

- 顶部安全条：`/api/status` → `publish_policy`
- 发布前预检：`/api/publish-preflight` 含待发布任务分布
- 队列列「发布配置」含有效行为徽章（`publish_effective_badge`）
- 真实模式：执行到点只创建/更新草稿；后台发布/定时发布必须人工完成

## 代码

- `publish_policy.py` — 策略解析
- `publish_config.should_submit_publish()` — 当前始终返回 false
- `scheduler/domain.py` — 执行草稿创建与 `publish_skipped_draft_only` 降级事件
