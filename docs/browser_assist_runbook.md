# browser_assist 操作清单（Round 18）

Status: Current — 与 `docs/wechat_browser_assist_strategy.md` 配套

## 适用场景

当 `wechat_field_matrix` 标记为 `unverified` / `partial` / `no`，且 `handling` 建议 **browser_assist + 人工确认** 时使用。典型字段：

- `cover_crop` — 封面裁剪效果需后台目视
- `wechat_backend_schedule` — 公众号后台定时群发（API 待核验）
- `show_cover_pic` — 封面是否显示在正文（API 待核验）

## 标准流程

1. **本地预检**：API 创建/更新草稿；记下 `article_id`、`media_id`。
2. **打开后台**：用户自行登录 [微信公众平台](https://mp.weixin.qq.com/) 草稿箱。
3. **核对字段**：按 dry-run 计划中的 `target_fields` 逐项确认。
4. **截图**：保存编辑页或预览截图（路径由用户选择，不入库 cookie）。
5. **人工确认**：用户点击保存；**默认不代为点击发布/群发**。
6. **回填 proof**（Round 19）：截图路径、链接、确认人、时间 → 本地状态 `waiting_confirmation` → `published`（有 proof 时）。

## 禁止项

- 保存密码、cookie、token
- 绕过验证码或扫码
- 自动最终发布或批量灌水
- 将未确认任务标为「已正式发布」

## 命令与 API

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan --article-id 1 --media-id MOCK_MEDIA_1
```

- Web：`GET /api/browser-assist-plan?article_id=&media_id=`
- 高级排错：`/debug` 加载 JSON

## dry-run 实现

逻辑见 `src/wechat_article_scheduler/adapters/browser_assist/workflow.py` 的 `build_dry_run_plan()`。
