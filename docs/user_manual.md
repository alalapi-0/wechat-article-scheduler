# 用户手册

## 1. 准备环境

见 README：venv、`.env`、`config/rules.yaml`。

## 2. 投递文章

支持 `articles/inbox/` 下：

- Markdown（可选 YAML frontmatter：`title`, `summary`）
- 纯文本
- HTML

## 3. 日常流程

1. `scan` — 导入并去重，文件移到 `imported/`
2. `plan` — 按规则生成未来发布时间
3. `run-once` 或 `scheduler` — 到期后创建 mock 草稿并标记发布

## 4. 驳回与重试

```bash
python -m wechat_article_scheduler.cli reject --article-id 1
python -m wechat_article_scheduler.cli retry-failed
```

## 5. 切换真实 API（高级）

在 `.env` 设置 `WECHAT_MODE=real` 并填写 `WECHAT_APP_ID`、`WECHAT_APP_SECRET`。当前代码仍为骨架，需完成 Round 3+ 实现后再用。
