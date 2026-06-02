# 封面裁剪与双比例预览（Round 62 / 收敛 Phase 1 Round 7）

## 比例

| 标签 | 比例 | 用途 |
|------|------|------|
| 横向 | 2.35:1 | 公众号文章封面条 |
| 方形 | 1:1 | 列表/头像区近似预览 |

## 配置字段 `cover_config_json`

```json
{
  "crop": { "x": 0.1, "y": 0.05, "width": 0.8, "height": 0.35 },
  "focal": { "x": 0.5, "y": 0.225 }
}
```

- `crop`：批量封面编辑器内 2.35:1 视口可见区域（归一化坐标）
- `focal`：由 `crop` 中心自动写入，供方形裁剪复用

## API

- `GET /api/articles/{id}/cover-previews` — 基于作品封面与配置
- `POST /api/cover-preview/dual` — `cover_path` + 可选 `cover_config_json`

## 渲染模式

- **Pillow 可用**：返回 `render_mode=jpeg` + `image_base64` 缩略图
- **无 Pillow**：`render_mode=css`，返回 `background_size` / `background_position`；Web 批量封面弹窗实时用同源 CSS 逻辑

## Web

批量设置封面 → 裁剪编辑器下方展示横向 + 方形双预览（拖动/缩放时同步更新）。

## 测试

```bash
python -m pytest tests/test_cover_crop_preview.py tests/test_web_batch_select.py -q
```
