# 微信草稿管理页面（Round 68 / 收敛 Round 13）

## 范围

- `wechat_drafts` 列表、按 `status` 筛选、关联作品标题与合集
- API：`GET /api/drafts`、`GET /api/drafts-summary`、`GET /api/drafts/{id}`
- Web：工作台 `#drafts` 区与独立页 `/drafts`

## 普通用户说明

- 列表仅包含本工具写入数据库的记录，**不是**公众号后台全部草稿。
- 演练模式（`WECHAT_MODE=mock`）下 `media_id` 为本地模拟，界面会标注「演练草稿」。

## 验证

```bash
python -m pytest tests/test_wechat_drafts_page.py -q
python scripts/agent_gate.py gate
```

浏览器（mock@8080）：`http://127.0.0.1:8080/#drafts` 与 `/drafts`，确认 `/api/drafts*` 无 network 错误。
