# 微信能力矩阵

| 能力 | 当前状态 | 模式 | 说明 |
|------|---------|------|------|
| token 获取与缓存 | 已实现 | real | `TokenCache` 内存缓存，不落盘 |
| 封面素材上传 | 已实现 | real | `material/add_material` |
| 草稿创建 | 已实现 | real/mock | real 调 `draft/add`，mock 本地生成 |
| 发布提交 | 已实现 | real/mock | 受 `WECHAT_ENABLE_PUBLISH` 控制 |
| 自动发布闸门 | 已实现 | real | Web 审核 + review_status，run-once 跳过未批准 |
| 扫描/排期/执行 CLI | 已实现 | all | 本地闭环保留 |
| Web 控制台高级能力 | 已实现 | all | 审核、定时 UX、预检清单 |
| Web 定时发布 UX | 已实现 | all | 人话计划时间与下一篇摘要 |
| 真实发布预检 | 已实现 | real | `/api/publish-preflight` 本地检查 |
| 完整封面裁剪流程 | 暂不做 | n/a | 本轮明确不实现 |
| 网页登录后台自动化 | 禁止 | n/a | 安全边界：不模拟后台登录 |
