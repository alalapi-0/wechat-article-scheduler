# 知乎 browser_assist 评估（Round 25）

Status: Evaluation / dry-run only — **不实现自动发文**

## 结论摘要

| 项 | 评估 |
|----|------|
| 是否适合 browser_assist | **有条件适合** |
| 风险 | 中高（登录、验证码、编辑器变更） |
| 推荐路径 | 先 `export-outbox --platform zhihu`，再人工登录 + 清单辅助 |
| 禁止 | 绕过登录/验证码、自动点击发布、保存 cookie |

## 干跑入口

```bash
WECHAT_MODE=mock python -m wechat_article_scheduler.cli browser-assist-plan --platform zhihu --article-id 1
```

- API：`GET /api/browser-assist-plan?platform=zhihu&article_id=1`
- 高级排错：`/debug` →「知乎 browser_assist 评估」

## 与 proof

browser_assist 任务应保持 `waiting_confirmation`，提交 proof 后才可标为已发布（见 `docs/proof_of_publish.md`）。

## 代码

`src/wechat_article_scheduler/adapters/browser_assist/zhihu_workflow.py`
