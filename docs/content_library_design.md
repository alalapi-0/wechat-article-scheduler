# 内容库设计

## 目标

将“文件扫描结果”演进为“可管理内容资产”，支持筛选、审核与复用。

## 当前状态

- 已实现：`articles` 表承载内容元数据；`collections` / `tags` / `article_tags`
- 已实现：扫描导入时写入默认集合与导入批次
- 已实现：多合集 `content/collections/*/collection.yaml` 扫描（见 `docs/multi_collection_library.md`）
- CLI：`content --limit N` 列出集合与条目

## 规划能力

- 集合（Collection）与标签（Tag）
- 审核状态（草稿/待审/通过/驳回）
- 来源追踪（source_path、content_hash、导入批次）

## 本轮限制

- 仅输出设计文档与代码骨架
- 不进行大规模模型与数据迁移
