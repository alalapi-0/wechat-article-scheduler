# 封面资产管理（Round 61 / 收敛 Phase 1 Round 6）

## 目录

| 目录 | 用途 |
|------|------|
| `articles/covers/` | 上传封面默认落盘（优先绑定） |
| `cover_assets/` | 素材库 |
| `assets/covers/` | 备用素材 |

## 能力

- **扫描**：统计素材、未绑定作品、无效路径、可 stem 绑定项、孤儿文件
- **绑定**：作品 `source_path` 文件名 stem 与封面文件名 stem 一致时写入 `articles.cover_path`
- **修复**：清除指向不存在文件的 `cover_path`
- **孤儿清理**：删除各素材目录中未被任何作品或默认封面引用的文件

## 入口

```bash
python -m wechat_article_scheduler.cli cover-scan
python -m wechat_article_scheduler.cli cover-scan --bind --repair
```

| API | 说明 |
|-----|------|
| `GET /api/covers/scan` | 完整扫描报告 |
| `POST /api/covers/bind` | 自动 stem 绑定 |
| `POST /api/covers/repair` | 修复无效路径 |
| `GET /api/covers/orphans` | 孤儿列表 |
| `POST /api/covers/cleanup-orphans` | 安全删除孤儿 |
| `GET /api/cover-assets` | 素材索引 + `scan_summary` |

发布时：`RealWechatAdapter` 优先单篇 `cover_path`，否则回退 `WECHAT_DEFAULT_THUMB_PATH`。

## 测试

```bash
python -m pytest tests/test_cover_manager.py tests/test_cover_assets.py -q
```
