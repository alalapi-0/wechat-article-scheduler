# 封面图资源

将公众号图文默认封面放在此目录（推荐 `covers/` 子目录）。

- 支持 **PNG**、**JPG** 等常见格式
- 在 `.env` 中设置路径（相对项目根目录），例如：

  ```bash
  WECHAT_DEFAULT_THUMB_PATH=assets/default_thumb.png
  ```

- 自定义封面示例：`assets/covers/my-cover.png`，并在 `.env` 中指向该路径
- 留空 `WECHAT_DEFAULT_THUMB_PATH` 时，real 模式会使用代码内置的最小占位 PNG
