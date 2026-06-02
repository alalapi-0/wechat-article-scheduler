# Phase 2 文本平台扩展（启动说明）

Status: Active — Phase 1 微信闭环已验收（round_076）

## 边界

- **不破坏** 微信公众号 scan/plan/run-once 主线
- 新能力以 `manual_export` outbox 为先：只导出、不联网、不自动发布
- 知乎/豆瓣等模板为复制说明，**不声称 API 已支持**

## 已实现（round_077+）

- 通用 outbox 导出：`export-outbox` CLI、`POST /api/articles/{id}/export-outbox`
- 平台提示文件：`--platform zhihu|douban` 生成 `zhihu_copy.md` 等

## 后续（backlog）

- Round 22 治理结论可并入本文件迭代
- browser_assist 评估（知乎/豆瓣）仍为 backlog
