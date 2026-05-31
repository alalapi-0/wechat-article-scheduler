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

- 若 `WECHAT_ENABLE_PUBLISH=false`：仅创建真实草稿，不提交发布。
- 若 `WECHAT_ENABLE_PUBLISH=true`：会提交发布；Web 工作台执行到点前会弹出二次确认并展示预检清单（模式 / 封面 / 摘要）。

## 6. 摘要与渲染说明

- digest 摘要统一上限 120 字，发布前会自动兜底截断并记录 warning 事件。
- Markdown 正文会按段落渲染为带 margin 的 `<p>` 标签（最小渲染骨架）。
