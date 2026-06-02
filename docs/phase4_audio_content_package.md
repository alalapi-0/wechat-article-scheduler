# Phase 4 音频/播客内容包预研

Status: Round 36+ / agent round_100（不上传）

## 字段

| 字段 | 说明 |
|------|------|
| audio_path | 主音频 |
| cover_path | 封面 |
| lyrics_path | 可选歌词 |
| show_notes_md | 播客文稿 |
| copyright_notice | 版权（建议必填） |
| rss_feed_url | 播客 RSS |

## Manifest 示例

- `manifests/examples/sample_audio_manifest.json`
- `manifests/examples/sample_podcast_manifest.json`

## CLI / API

```bash
python -m wechat_article_scheduler.cli audio-package-plan --platform podcast
python -m wechat_article_scheduler.cli manifest-validate --manifest manifests/examples/sample_podcast_manifest.json
```

- `GET /api/audio-package-plan?platform=podcast`
- `GET /api/audio-package/platforms`

Registry 占位：`podcast`、`netease_music` + manual_export（未实现真上传）。
