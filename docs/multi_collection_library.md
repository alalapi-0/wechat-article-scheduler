# 多合集内容库（Round 63 / 收敛 Phase 1 Round 8）

## collection.yaml

```yaml
slug: demo
name: 演示合集
description: 专栏说明
volume_label: 卷
title_template: "【{title}】"
default_cover: assets/covers/demo.png
sort_rule: source_name
legacy_inbox_subdir: demo
```

## 扫描

- `python -m wechat_article_scheduler.cli scan`：先扫 `articles/inbox` 根文件（默认合集），再扫各合集 inbox
- 导入目录：`articles/imported/{slug}/`（合集）或 `articles/imported/`（默认）

## API

| 路径 | 说明 |
|------|------|
| `GET /api/collections` | 合集列表 + 作品数 |
| `GET /api/articles?collection=demo` | 按合集筛选 |
| `GET /api/content-library` | 内容库视图（含合集） |

## Web

作品库工具栏「合集」下拉筛选；卡片展示合集名称 chip。

## 测试

```bash
python -m pytest tests/test_multi_collection.py tests/test_content_library.py -q
```
