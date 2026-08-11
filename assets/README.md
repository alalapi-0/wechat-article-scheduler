# 封面资源

real 模式创建微信公众号草稿时必须有真实、可读取且非空的封面图片。可以：

- 在 Web 工作台给文章绑定独立封面；或
- 在本地 .env 设置 WECHAT_DEFAULT_THUMB_PATH，指向非空的 JPG/JPEG 或 PNG 文件。

仓库不提供可用于真实草稿的占位封面。缺少有效封面时，预检和 real adapter 都会在任何 HTTP 请求前失败。
