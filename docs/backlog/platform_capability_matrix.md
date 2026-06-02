# 平台能力矩阵

Status: Backlog / Not current development target

本矩阵是规划文档，不表示已经支持所有平台。所有未确认官方 API 的平台均标记为 `unknown_need_verify`。

| platform | content_types | adapter_type_preference | official_api_status | browser_assist_status | manual_export_status | login_risk | captcha_risk | media_requirements | title_limit | body_limit | description_limit | cover_requirements | scheduling_support | proof_required | current_priority | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| wechat_mp | article, longform | official_api | partially_verified_draft | not_needed | possible | low | low | thumb required for draft | need_verify | need_verify | digest 120 | thumb image | API draft done, publish gated | false for official_api draft | highest | 当前优先级最高，已部分跑通草稿创建 |
| zhihu | article | browser_assist, manual_export | unknown_need_verify | planned | planned | medium | medium | cover optional need verify | unknown_need_verify | unknown_need_verify | unknown_need_verify | need_verify | unknown_need_verify | true | phase_2_text | 第二阶段文本平台，先 manual_export/browser_assist |
| douban | note, status | browser_assist, manual_export | unknown_need_verify | planned | planned | medium | medium | image optional need verify | unknown_need_verify | unknown_need_verify | unknown_need_verify | need_verify | unknown_need_verify | true | phase_2_text | 第二阶段文本平台，先 manual_export/browser_assist |
| wechat_channels | video | browser_assist, manual_export | unknown_need_verify | planned | planned | high | high | video, cover | unknown_need_verify | n/a | unknown_need_verify | strict need verify | unknown_need_verify | true | later_high_risk | 高风控，默认 browser_assist + waiting_confirmation |
| kuaishou | video | browser_assist, manual_export | unknown_need_verify | planned | planned | high | high | video, cover | unknown_need_verify | n/a | unknown_need_verify | strict need verify | unknown_need_verify | true | later_high_risk | 高风控，默认 browser_assist + waiting_confirmation |
| xiaohongshu | note, video | browser_assist, manual_export | unknown_need_verify | planned | planned | high | high | images/video, cover | unknown_need_verify | unknown_need_verify | unknown_need_verify | strict need verify | unknown_need_verify | true | later_high_risk | 高风控，manual_export 优先 |
| douyin | video | browser_assist, manual_export | unknown_need_verify | planned | planned | high | high | video, cover | unknown_need_verify | n/a | unknown_need_verify | strict need verify | unknown_need_verify | true | later_high_risk | 高风控，默认不自动发布 |
| bilibili | video | manual_export, browser_assist | unknown_need_verify | planned | planned | medium | medium | video, cover, tags | unknown_need_verify | n/a | unknown_need_verify | strict need verify | unknown_need_verify | true | phase_3_video | 可能存在可研究工具链，本轮不验证 |
| netease_music | audio, music | manual_export | unknown_need_verify | not_planned | planned | high | medium | audio, cover, lyrics | unknown_need_verify | n/a | unknown_need_verify | copyright sensitive | unknown_need_verify | true | low | 涉及音频、版权、审核，优先级靠后 |
| future_podcast | audio | manual_export, webhook | unknown_need_verify | not_planned | planned | medium | medium | audio, cover, rss | unknown_need_verify | n/a | unknown_need_verify | need_verify | unknown_need_verify | true | reserved | 播客平台预留 |

## 明确判断

- 微信公众号当前优先级最高，因为已经部分跑通。
- 知乎、豆瓣适合第二阶段文本平台扩展，但大概率先 `browser_assist` 或 `manual_export`。
- 小红书、视频号、抖音、快手属于高风控平台，默认 `browser_assist + waiting_confirmation`。
- Bilibili 可能存在相对可研究的上传接口或工具链，但本轮不验证。
- 网易云音乐涉及音频、版权、审核，优先级靠后。
- 所有未确认官方 API 的平台都标记 `unknown_need_verify`。
- 不允许文档假装已经支持某个平台。
