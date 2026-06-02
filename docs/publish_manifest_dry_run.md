# publish_manifest 干跑

Status: 实验性（round_086–087）

按 `docs/backlog/multi_project_manifest_design.md` 校验 `publish_manifest.json`，并生成 `ContentPackageDraft` / `PlatformPayloadDraft` 预览。**不写入 SQLite**；微信公众号仍走 `scan` / `plan`。

## 示例

`manifests/examples/sample_publish_manifest.json`

## CLI

```bash
python -m wechat_article_scheduler.cli manifest-validate --manifest manifests/examples/sample_publish_manifest.json
python -m wechat_article_scheduler.cli manifest-dry-run --manifest manifests/examples/sample_publish_manifest.json
```

## API

- `GET /api/manifest/sample-dry-run` — 对仓库内示例 manifest 干跑
