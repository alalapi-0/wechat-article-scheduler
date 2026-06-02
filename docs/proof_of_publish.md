# proof_of_publish（Round 19）

Status: Current — 半自动发布结果证明

## 字段

| 字段 | 说明 |
|------|------|
| `screenshot_path` | 本地截图路径（不入库 cookie/密码） |
| `public_url` | 公众号或外链公开地址 |
| `confirmed_by` | 确认人（昵称或标识） |
| `confirmed_at` | 确认时间（ISO/ SQLite datetime） |
| `note` | 可选备注 |

至少提供 `public_url` 或 `screenshot_path` 之一，方可将 `waiting_confirmation` 任务标记为已完成。

## 状态规则

- `publish_jobs.status = waiting_confirmation`：材料已就绪，**未**确认平台已发布。
- 提交 proof 后：`status → done`，`articles.status → published`（演练模式同样只更新本地记录）。
- 无 proof 不得从 `waiting_confirmation` 进入 `done` / 文章 `published`。

## 接口

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli mark-waiting-confirmation --job-id 1
WECHAT_MODE=mock python -m wechat_article_scheduler.cli submit-proof --job-id 1 --public-url https://example.com/p --confirmed-by 本地用户
```

- `GET /api/publish-jobs/{job_id}/proof`
- `POST /api/publish-jobs/{job_id}/proof`（JSON body）
- `GET /api/waiting-confirmation`
- 作品详情页：待确认任务显示回填表单

## 实现

`src/wechat_article_scheduler/review/proof.py`
