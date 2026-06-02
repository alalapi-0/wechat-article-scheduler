# 豆瓣 browser_assist 评估（Round 27）

Status: Evaluation / dry-run only

## 结论

| 项 | 评估 |
|----|------|
| 适合 browser_assist | **有条件适合** |
| 风险 | 中等 |
| 推荐 | 先 `export-outbox --platform douban`，再人工登录 + 清单辅助 |

## 入口

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan --platform douban
```

- API：`GET /api/browser-assist-plan?platform=douban`
- `/debug` →「豆瓣 browser_assist 评估」

## 禁止

- 绕过登录/验证码
- 自动发布
- 保存 cookie

代码：`adapters/browser_assist/douban_workflow.py`
