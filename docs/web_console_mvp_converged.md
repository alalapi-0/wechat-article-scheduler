# Web 控制台 MVP（收敛 Round 10 / agent round_065）

## 普通用户视图（Desktop-first）

- 顶部：运行模式安全条 + **显示高级信息** 开关（默认关）
- 左侧主栏：概览统计、**下一步**提示、作品库、回收站
- 右侧：发布计划（**扫描本地收件箱** / 自动推荐 / 执行到点）、三步主操作、**发布队列**（待发布/发布中/已完成/失败/全部）、操作记录

## API

| 端点 | 用途 |
|------|------|
| `GET /api/overview` | 统计 + `workbench` 下一步 + 排期摘要 |
| `GET /api/jobs?status=pending` | 队列表格数据源 |
| `POST /api/scan` | 扫描 `articles/inbox` 与合集 inbox |
| `POST /api/plan` | 自动排期 |
| `POST /api/run-once` | 执行到点任务 |

## 验证

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli serve
python -m pytest tests/test_web_console_mvp.py tests/test_web_app.py -q
```

浏览器：打开 `http://127.0.0.1:8080/`，确认 overview/jobs/scan 等核心 API 200，console 无 error。
