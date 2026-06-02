# 公众号效果预览快照（Round 60 / 收敛 Phase 1 Round 5）

## 目标

发布前在本地看到**近似**公众号正文效果：摘要、HTML 正文、封面、质量提示；与 `draft/add` 同源 `render_for_publish`。

## 统一入口

| 入口 | 说明 |
|------|------|
| `build_article_preview_package()` | Python 预览包（摘要 120 字、封面 URL、content_hints、近似说明） |
| `GET /api/articles/{id}/render-preview` | Web/API；`?save_snapshot=true` 可选落盘 |
| `POST /api/articles/{id}/preview-snapshot` | 显式保存快照 |
| `python -m wechat_article_scheduler.cli preview-snapshot --article-id N` | CLI |

## 存储

- 目录：`storage/preview_snapshots/`
- 文件：`article_{id}_{UTC}.json` + 同名 `.html`
- 运行时产物不入库（见 `.gitignore`）

## 近似说明

预览标注 `approximation_note`：本地渲染不等同于微信后台编辑器；标题在公众号标题栏单独显示。

## 测试

```bash
python -m pytest tests/test_preview_snapshot.py tests/test_web_app.py -q -k preview
```
