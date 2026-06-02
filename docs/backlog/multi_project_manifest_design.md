# 多项目 Manifest 设计

Status: Backlog / Not current development target

## 目标

每个创作项目只需要输出 `publish_manifest.json`，发布器统一读取、导入、排期、适配和审计。发布器不侵入每个创作项目内部。

## manifest 示例

```json
{
  "schema_version": 1,
  "project_id": "novel-hero-translation",
  "package_id": "chapter-001",
  "content_type": "article",
  "title": "001 是谁杀死了勇者",
  "summary": "本文为个人翻译与学习整理。",
  "body_md": "content/collections/hero/articles/001.md",
  "media_refs": [
    {
      "path": "content/collections/hero/covers/main.png",
      "role": "cover"
    }
  ],
  "targets": [
    {
      "platform_account_id": "wechat_mp_main",
      "adapter_type": "official_api",
      "scheduled_at": "2026-06-02T20:00:00+08:00",
      "review_required": false,
      "extra": {
        "need_open_comment": 0,
        "only_fans_can_comment": 0
      }
    },
    {
      "platform_account_id": "zhihu_main",
      "adapter_type": "browser_assist",
      "scheduled_at": "2026-06-03T20:00:00+08:00",
      "review_required": true
    }
  ]
}
```

## 1. schema_version 演进

`schema_version` 从 1 开始。新增可选字段时小版本兼容；删除或改名必须升大版本并提供迁移说明。

## 2. project_id 稳定性

`project_id` 是来源项目稳定身份，不应随目录移动变化。可由用户配置，不建议自动用目录名推断。

## 3. package_id 防重复

`package_id` 在同一个 `project_id` 下唯一。导入时以 `project_id + package_id` 判断同一内容包。

## 4. media_refs 解析

`media_refs.path` 相对 manifest 所在目录解析。导入时计算 sha256，写入或复用 `media_asset`。

## 5. targets 生成 publish_job

每个 target 生成一个 `platform_payload` 和一个 `publish_job`。同一内容包多个 target 互不污染状态。

## 6. review_required 影响状态机

`review_required=true` 时，payload dry-run 通过后进入 `waiting_confirmation` 或等待 approve，再进入 scheduled。

## 7. 内容类型扩展

- `body_md`：Markdown 文章。
- `body_html`：HTML 文章。
- `video_path`：视频内容。
- `audio_path`：音频内容。
- `lyrics_path`、`subtitle_path`：音频/视频附属文件。

## 8. hash 和幂等

导入时计算 manifest hash 和内容 hash。相同 hash 重复导入应跳过；内容变化时生成新的导入记录并重新 dry-run。
