# Review and Proof 设计

Status: Backlog / Not current development target

## 定位

Review and Proof 吸收 BrightBean 的审批与确认思想，但保持个人工具轻量化。它不恢复当前微信公众号链路的内容审核门禁，只服务多平台、无官方 API、高风险平台和半自动发布。

## 1. 哪些平台需要 review_required

默认需要 `review_required` 的情况：

- `browser_assist` 适配器。
- `manual_export` 适配器。
- 高风控平台：小红书、抖音、快手、微信视频号。
- 未验证官方 API 的平台。
- 需要人工检查版权、音频、视频、封面或敏感信息的平台。

## 2. waiting_confirmation 状态

`waiting_confirmation` 表示系统已准备好发布材料或辅助步骤，但不能确认平台已经发布。

- browser_assist 填表后进入该状态。
- manual_export 生成 outbox 后进入该状态。
- 用户提交 proof 前不得自动改为 `published`。

## 3. approve / reject / changes_requested

- `approve`：允许进入下一步发布准备或辅助流程。
- `reject`：取消任务并记录原因。
- `changes_requested`：要求修改 payload 或内容包后重新 dry-run。

## 4. proof_of_publish

人工发布后提交 proof，系统才能确认半自动任务结果。

## 5. proof 类型

- 平台链接。
- 平台 post id。
- 截图路径。
- 手动备注。

## 6. browser_assist 不得直接标记 published

browser_assist 只能辅助，不能绕过人工确认，也不能自动点击最终发布。

## 7. manual_export 不得直接标记 published

manual_export 只生成 outbox 包。用户复制上传后必须提交 proof。

## 8. official_api 可直接 published

official_api 返回平台 ID 或成功响应后可直接标记 `published`，但必须记录 `publish_attempt`。

## 9. 无 proof 的半自动任务

没有 proof 的任务应停留在 `waiting_confirmation` 或 `submitted_unverified`，不得伪装为成功发布。

## 10. Web 控制台展示

未来 Web 控制台应展示：

- 待确认队列。
- payload 预览。
- 操作说明。
- proof 上传入口。
- 最近 attempt 和错误摘要。
- 高级信息中的原始响应片段。
