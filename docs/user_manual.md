# 用户手册

## 1. 准备环境

见 README：venv、`.env`、`config/rules.yaml`。

## 2. 投递作品

**推荐：网页批量上传。** 启动 `serve` 后在工作台「作品库」拖拽上传，或点「选择作品文件 / 选择封面图」：

- 作品文件：Markdown（可选 YAML frontmatter：`title`, `summary`）/ 纯文本 / HTML
- 封面图：jpg / png / gif / webp；按文件名（去扩展名）自动绑定到同名作品，每篇也可单独「换封面」
- 没有"审核"步骤：上传即视为想发布的作品

也可用 CLI：把文件放入 `articles/inbox/` 后执行 `scan`。

## 3. 日常流程

1. **上传作品与封面**（网页拖拽，或 CLI `scan` 导入去重，文件移到 `imported/`）
2. `plan` / 点「安排发布时间」 — 按规则生成未来发布时间
3. `run-once` / 点「执行到点发布」（或 `scheduler`）— 到期后创建草稿并标记发布；真实模式执行前会二次确认

## 4. 从发布流程移除与重试

```bash
python -m wechat_article_scheduler.cli reject --article-id 1
python -m wechat_article_scheduler.cli retry-failed
```

## 5. 切换真实 API（高级）

在 `.env` 设置 `WECHAT_MODE=real` 并填写 `WECHAT_APP_ID`、`WECHAT_APP_SECRET`。

- `WECHAT_MODE=real` 是真实 API 测试模式；建议配合 `WECHAT_ENABLE_PUBLISH=false` 做草稿-only 验证。
- 批量验证入口：`python3 scripts/real_api_check.py --samples 3`（报告见 `reports/real_api_runs/`）。
- 无凭证时：`python3 scripts/real_api_check.py --dry-run --skip-if-blocked`（写报告、退出 0，不打印 secret）。
- 任务级选择“正式发布”且 `WECHAT_ENABLE_PUBLISH=true` 时才会提交发布；Web 执行到点前二次确认并展示预检清单。

当前定时发布是本地 scheduler 到点调用 API，不是把定时时间写入微信后台草稿箱。后者需要单独核验微信官方 API 是否支持；不支持时走 browser_assist + 人工确认。

## 6. Scheduler 常驻运行（本地）

默认 `WECHAT_MODE=mock` 演练，不联网。需要长期到点发布时，用 **CLI 进程** 或 **系统定时任务**，不要依赖浏览器标签页一直开着。

| 方式 | 适用 | 启动 | 停止 |
|------|------|------|------|
| 前台 / tmux | 本机调试 | `python -m wechat_article_scheduler.cli scheduler-daemon` | Ctrl+C |
| launchd | macOS | 见 `deploy/examples/scheduler/*.plist.example` | `launchctl stop` |
| systemd | Linux | 见 `deploy/examples/scheduler/*.service.example` | `systemctl stop` |
| cron | 轻量 | `scripts/cron_run_once.sh`（每分钟） | 删 crontab 行 |

完整步骤、日志路径与故障处理见 **`docs/scheduler_runbook.md`**。健康检查：`scheduler-health`。勿同时跑常驻 `scheduler` 与 cron `run-once`（会争用锁）。

## 7. 摘要与渲染说明

- digest 摘要统一上限 120 字，发布前会自动兜底截断并记录 warning 事件。
- Markdown 正文会按段落渲染为带 margin 的 `<p>` 标签（最小渲染骨架）。
