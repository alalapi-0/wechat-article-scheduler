# 封面图资源

将公众号图文默认封面放在 `covers/` 子目录。

## 推荐命名

- 默认封面：**`assets/covers/default_cover.jpg`**（或 `.png`）
- 在 `.env` 中设置（相对项目根目录）：

  ```bash
  WECHAT_DEFAULT_THUMB_PATH=assets/covers/default_cover.jpg
  ```

## 格式

- 支持 **JPG**、**PNG** 等常见格式；real 模式上传时会按扩展名/文件头选择正确的 `Content-Type` 与文件名（`thumb.jpg` / `thumb.png`）
- 仓库内置占位：`assets/default_thumb.png`（`.env.example` 默认值）
- 留空 `WECHAT_DEFAULT_THUMB_PATH` 时，real 模式会使用代码内置的最小占位 PNG

## 首次联调建议

```bash
WECHAT_MODE=real
WECHAT_ENABLE_PUBLISH=false   # 仅创建草稿，不提交发布
DRY_RUN=false
```
