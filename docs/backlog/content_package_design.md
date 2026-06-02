# Content Package 设计

Status: Backlog / Not current development target

## 目标

`content_package` 将文章、章节、视频、音频、封面和平台字段统一成一次发布单元。它是未来多项目、多平台、多媒体能力的核心抽象。

## 当前兼容

当前 `articles` 表仍是微信公众号文章链路的实现事实。`content_package` 不能一次性替换 `articles`，应通过兼容导入逐轮落地。

## 基本结构

- `package_id`：创作项目内稳定唯一。
- `project_id`：来源项目稳定 ID。
- `content_type`：`article/chapter/longform/note/video/audio/music`。
- `title`：主标题。
- `summary`：摘要。
- `canonical_text_path`：主内容路径。
- `metadata_json`：标签、合集、作者、语言等扩展字段。
- `media_asset_ids`：封面、图片、视频、音频等资产。

## 生命周期

- `draft`：导入但未准备好。
- `ready`：内容完整，可生成 payload。
- `locked`：已进入发布队列，避免无审计修改。
- `archived`：归档，不再发布。

## 与 platform_payload 的关系

一个 `content_package` 可生成多个 `platform_payload`。payload 保存平台变体，不修改主内容。

## 与 media_asset 的关系

媒体资产按 hash 去重，同一个封面或视频可被多个内容包引用。

## 风险边界

- 不把视频/音频发布直接塞进当前文章表。
- 不要求所有历史文章立即迁移。
- 不把平台限制写死在 content package 内。
