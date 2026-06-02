# 多合集内容库

每个子目录一份 `collection.yaml`，扫描时同步到 SQLite `collections` 表。

## 收件箱路径（按优先级尝试）

1. `inbox_dir`（yaml 内可选）
2. `content/collections/{slug}/inbox/`
3. `articles/inbox/{legacy_inbox_subdir}/`（默认 subdir 与 slug 相同）

根目录 `articles/inbox/*.md` 仍进入**默认合集**，与旧行为兼容。

详见 `docs/multi_collection_library.md`。
