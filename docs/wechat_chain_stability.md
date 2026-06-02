# 微信公众号主链路稳定性（Round 57）

Status: Phase 1 / 收敛路线图 Round 2

## 主链路

```text
articles/inbox  →  scan  →  articles(imported)
                         →  plan  →  publish_jobs(pending)
                         →  run-once / scheduler  →  adapter.create_draft
                                              →  adapter.submit_publish (可跳过)
                         →  wechat_drafts + events
```

## 模式对照

| 配置 | 联网 | 创建草稿 | freepublish/submit |
|------|------|----------|-------------------|
| `WECHAT_MODE=mock`（默认） | 否 | mock media_id | 始终 skipped |
| `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH=false` | 是 | 真实 draft/add | skipped（draft-only） |
| `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH=true` + 任务 `publish_action=publish` | 是 | 真实 draft/add | 执行提交 |

任务级 `publish_action=draft` 时，即使全局开启 publish，也不会调用 `freepublish/submit`（见 `should_submit_publish`）。

## CLI 入口

| 命令 | 作用 |
|------|------|
| `scan` | 收录 inbox → `articles` |
| `plan` | 生成 `publish_jobs` |
| `run-once` | 执行到期 pending 任务 |
| `scheduler` | 轮询 `run-once` |

## 回归测试

- `tests/test_wechat_chain_stability.py` — mock 端到端 scan → plan → run-once
- `tests/test_scheduler_hardening.py` — dry-run、重试上限、real draft-only
- `tests/test_publish_config.py` — `should_submit_publish` 矩阵

## 已知边界

- 无微信凭证时：保持 `WECHAT_MODE=mock`，不硬停 Agent 门控。
- 内容质量阻断（正文空等）仅作用于 **真实正式发布** 路径，见 `content_quality.content_block_reason`。
- 定时时间写入微信后台草稿箱不在当前 API 能力内；见 `docs/wechat_browser_assist_strategy.md`。
