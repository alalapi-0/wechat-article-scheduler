# 平台优先级

Status: Current P0 priority policy

除微信公众号外，其他平台当前不进入开发。

| 平台 | 当前优先级 | 当前开发 | 推荐接入方式 | 需要 browser_assist | 需要 proof_of_publish | 风控风险 | API 确认 | 推进或暂缓原因 |
|---|---|---:|---|---:|---:|---|---|---|
| `wechat_mp` | P0 | 是 | official_api；必要时 browser_assist | 可选 | 正式发布或人工流程需要 | 中 | 已有真实草稿验证 | 当前主线，先打通个人本地微信公众号闭环 |
| `zhihu` | P1 | 否 | manual_export -> browser_assist 评估 | 可能 | 是 | 中 | 未确认 | 文本平台可后续扩展，但阶段一不开发 |
| `douban` | P1 | 否 | manual_export -> browser_assist 评估 | 可能 | 是 | 中 | 未确认 | 文本平台可后续扩展，但阶段一不开发 |
| `wordpress` / `local_blog` | P1 | 否 | local export 或 official API 评估 | 否 | 可选 | 低到中 | 未确认 | 更适合阶段二，等微信闭环稳定后评估 |
| `xiaohongshu` | P2 | 否 | manual_export 优先，browser_assist 谨慎评估 | 可能 | 是 | 高 | 未确认 | 图文/视频和风控复杂，暂缓 |
| `bilibili` | P2 | 否 | manual_export 优先，API/工具链预研 | 可能 | 是 | 中到高 | 未确认 | 视频资产复杂，暂缓 |
| `wechat_channels` | P2 | 否 | manual_export 或 browser_assist 评估 | 可能 | 是 | 高 | 未确认 | 视频号不等于公众号，暂缓 |
| `douyin` | P2 | 否 | manual_export 优先 | 可能 | 是 | 高 | 未确认 | 短视频平台风控高，暂缓 |
| `kuaishou` | P2 | 否 | manual_export 优先 | 可能 | 是 | 高 | 未确认 | 短视频平台风控高，暂缓 |
| `netease_music` | P3 | 否 | manual_export 或独立预研 | 可能 | 是 | 高 | 未确认 | 音频、版权和审核复杂，长期 backlog |
| `podcast` | P3 | 否 | RSS / webhook / manual_export 评估 | 否 | 可选 | 中 | 未确认 | 音频平台阶段四再考虑 |

## P0 当前主线

- `wechat_mp`

当前所有产品、架构、测试和文档工作都必须优先保护微信公众号 scan / plan / run-once / 草稿创建链路。

## P1 文本平台后续

- `zhihu`
- `douban`
- `wordpress`
- `local_blog`

这些平台只能进入 backlog。阶段二启动前必须先做文本平台扩展治理轮。

## P2 图文/视频平台

- `xiaohongshu`
- `bilibili`
- `wechat_channels`
- `douyin`
- `kuaishou`

这些平台当前不开发，不建立 adapter，不写发布流程，不扩展数据库。

## P3 音频/音乐平台

- `netease_music`
- `podcast`

这些平台当前只保留为长期备选。

## 当前结论

微信公众号是唯一当前开发平台。其他平台可以被记录、归档、评估，但不得成为阶段一实现任务。
