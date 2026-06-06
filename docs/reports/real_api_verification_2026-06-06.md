# 真实 API 验证记录（2026-06-06）

> 不含密钥；仅 `[API-TEST]` 内容创建/删除。

## 环境

| 项 | 值 |
|---|---|
| WECHAT_MODE | real |
| WECHAT_ENABLE_PUBLISH | false |
| 凭证 | .env 已配置（未读取/打印 secret） |

## 结果摘要

| 检查项 | 结果 | 说明 |
|---|---|---|
| sync-remote（draft/batchget 分页） | **PASS** | 首次同步 5 篇；创建测试稿后再同步 6 篇（+1 inserted） |
| capability draft_list | **PASS** | state=authorized，item_count=1（探测页） |
| capability published_list | **PASS** | state=**unauthorized**（errcode 48001），显示「未授权」而非「0 篇」 |
| real_api_check --samples 1 | **PASS** | token_ok=true，success=1，未调用 freepublish/submit |
| 创建 [API-TEST] 草稿 | **PASS** | 样本 `01_normal`，报告见 `reports/real_api_runs/run_20260606T054635Z.json` |
| 按 media_id 删除测试稿 | **PASS** | 仅删除本会话新建 1 篇，success=1 failure=0 |
| 非测试远端内容 | **未触碰** | 其余草稿仅同步镜像，未删除 |

## 命令

```bash
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python -m wechat_article_scheduler.cli sync-remote
WECHAT_MODE=real WECHAT_ENABLE_PUBLISH=false python scripts/real_api_check.py --samples 1
```

## 备注

- 账号无 `freepublish/batchget` 权限，已发布删除 UI 应保持禁用。
- 历史 `[API-TEST]` 草稿可能仍存在于远端；本次仅清理本会话新建条目。
