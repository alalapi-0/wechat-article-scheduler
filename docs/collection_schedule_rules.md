# 合集排期规则（Round 64 / 收敛 Phase 1 Round 9）

## 概述

自动 `plan` 按**合集**分组排期：每合集可覆盖全局 `config/rules.yaml` 中的 `schedule` 参数；跨合集沿用全局最小间隔，并支持 `stagger_hours` 错峰。

## 配置

### 全局（`config/rules.yaml`）

```yaml
schedule:
  max_per_day: 2
  min_hours_between: 4
  preferred_hours: [9, 14, 20]
  window_days: 14   # 可选，默认用 AppConfig.schedule_window_days
```

### 合集（`content/collections/<slug>/collection.yaml`）

```yaml
schedule:
  max_per_day: 1
  min_hours_between: 6
  preferred_hours: [10, 18]
  stagger_hours: 2      # 相对上一合集末次排期的额外小时
  window_days: 14       # 可选，覆盖全局窗口
```

解析结果写入 `collections.config_json` 的 `schedule` 字段，供未扫描到 YAML 时从数据库回退。

## 行为

1. 仅处理 `status=imported` 且无 `pending`/`running` 任务的文章。
2. 按合集 slug 分组；处理顺序：`default` 优先，其余按 slug 字母序。
3. 每日上限计数键：`{collection_slug}:{YYYY-MM-DD}`。
4. 跨合集间隔：`max(全局 min_hours_between, 合集 min_hours_between)`。
5. `build_plan` 返回 `planned`、`skipped_has_job`、`by_collection`、`hints`（窗口满、各合集摘要）。

## 相关代码

- `src/wechat_article_scheduler/content_library/collection_schedule.py`
- `src/wechat_article_scheduler/plan.py`
- Web 文案：`humanize_plan_result`（`/api/plan` 的 `human` 字段）

## 测试

```bash
python -m pytest tests/test_collection_schedule.py tests/test_web_schedule.py -q
```
