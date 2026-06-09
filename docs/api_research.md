# 微信公众平台 API 调研

> 基于官方文档整理，2026-06-06 复核。接入前请在公众平台确认账号类型与接口权限。

## 认证

- **access_token**：`GET https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET`
- Token 有效期约 2 小时，需本地缓存刷新（本项目 Round 3 仅骨架，未实现自动刷新）。
- 第三方平台可使用 `authorizer_access_token`（代运营场景）。

## 草稿箱

| 接口 | 方法 | 说明 |
|------|------|------|
| [新增草稿](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_add.html) | `POST /cgi-bin/draft/add` | Body: `articles[]`，含 `title`, `author`, `digest`, `content`, `thumb_media_id` 等 |
| [获取草稿列表](https://developers.weixin.qq.com/doc/subscription/api/draftbox/draftmanage/api_draft_batchget.html) | `POST /cgi-bin/draft/batchget` | 分页 `offset` / `count` |

注意：

- 正文 HTML 内图片 URL 须来自「上传图文消息图片」接口，外链会被过滤。
- 群发或发布后草稿会从草稿箱移除。

## 发布

| 接口 | 方法 | 说明 |
|------|------|------|
| [发布草稿](https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_submit.html) | `POST /cgi-bin/freepublish/submit` | Body 只有 `media_id`；异步结果通过回调 `PUBLISHJOBFINISH` |

常见错误码：`48001` 未授权、`53503` 草稿未通过检查。

官方[发布能力](https://developers.weixin.qq.com/doc/service/guide/product/publish.html)列出了发布列表、删除、状态、详情和提交发布接口，没有“写入后台定时时间”的接口。后台定时发布不能由草稿 API 或 `freepublish/submit` 设置。

当前账号截图显示上述发布接口均为“无权限”，草稿接口均为“有权限”。因此它可以管理草稿，但不能使用本地 scheduler 到点调用发布接口。

## 本项目策略

- 默认 `WECHAT_MODE=mock`，`MockWechatAdapter` 生成本地 `mock_media_*` id。
- `RealWechatAdapter` 在 `WECHAT_MODE=real` 且凭证齐全时调用：token 缓存 → thumb 上传 → `draft/add` → `freepublish/submit`（可通过 `WECHAT_ENABLE_PUBLISH=false` 跳过发布）。
- 单元测试 mock HTTP，不默认联网。
- **当前账号固定策略**：`WECHAT_ENABLE_PUBLISH=false`，发布与后台定时走能力门控和外部任务包。
- **待人工确认**：封面 `thumb_media_id` 获取流程、是否需素材库永久 media。

## 安全

- AppSecret 仅放 `.env`，禁止入库与日志。
- 禁止 Cookie 模拟后台发文。
