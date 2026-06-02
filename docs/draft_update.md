# 微信草稿更新（Round 71 / 收敛 Round 16）

## 能力

- **微信 API**：`cgi-bin/draft/update`（`WECHAT_MODE=real` 且凭证齐全）
- **演练**：`MockWechatAdapter.update_draft` 保留原 `media_id`，仅更新本地 `wechat_drafts` 记录
- **幂等**：`content_fingerprint`（标题+摘要+正文+封面路径）；未改内容则跳过
- **历史**：旧记录标记 `superseded`，新记录 `updated`，不丢弃旧 `media_id`

## 用法

```bash
# 需已有 wechat_drafts 记录（通常来自 run-once）
python -m wechat_article_scheduler.cli update-draft --article-id 1
```

Web：作品详情页 **更新微信草稿** → `POST /api/articles/{id}/update-draft`

## 不可更新时

- 尚无草稿：先安排发布并执行 `run-once`（或 Web「执行到点发布」）
- API 报错：查看 `events` 中 `draft_updated` / 失败原因；可改内容后重试
- 后台 DOM 改稿：见 `docs/wechat_browser_assist_strategy.md`（非默认路径）

## 验证

```bash
python -m pytest tests/test_draft_update.py tests/test_mock_adapter.py tests/test_real_adapter.py -q
```
