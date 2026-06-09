# 草稿权限账号落地方案

Status: Current — based on account capability screenshots and browser validation through 2026-06-07

## 结论

当前账号可通过官方 API 管理草稿，但不能通过官方 API 发布文章，也不能把计划时间写入微信后台：

- 草稿 API 可用：新增、更新、列表、总数、详情、删除。
- 发布 API 不可用：`freepublish/submit`、发布列表、发布状态、已发布详情和删除已发布文章均无权限。
- 微信后台定时不是草稿 API 权限。官方 `freepublish/submit` 请求体只有 `media_id`，没有定时时间字段。

因此，项目的真实目标应改为：

> 每周批量整理和更新草稿，由浏览器 Agent 完成发布前字段设置并保存；用户本人只负责最终发表、安全验证及必要的目标时间回填。

当前账号不能使用“本地 scheduler 到点调用 `freepublish/submit`”完成正式发布。

## 两种“定时发布”

| 方式 | 所需权限 | 当前账号 | 项目处理 |
|---|---|---|---|
| 本地 scheduler 到点调用 `freepublish/submit` | 发布草稿接口权限 | 不可用 | 必须禁用 |
| 在公众号后台填写定时时间，由微信后台执行 | 后台页面操作能力 | API 不提供 | 用户人工后台操作 + proof |

这两种方式不能混为一谈。草稿列表权限只证明能管理草稿，不证明能发布。

## 当前账号可实现的能力

| 能力 | 结论 | 落地方式 |
|---|---|---|
| 读取并镜像远端草稿 | 可实现 | `draft/batchget` |
| 新建、更新、删除草稿 | 可实现 | 官方草稿 API |
| 批量设置标题、正文、摘要、作者、留言字段 | 可实现 | 草稿 API |
| 固定合集 | API 不支持 | 后台/外部 Agent |
| 推荐、通知 | API 不支持 | 后台/外部 Agent |
| 封面显示和裁剪确认 | API 未接线或需目视 | 后台/外部 Agent |
| 微信后台定时 | API 不支持 | 浏览器 Agent 填写目标时间并保存草稿；用户最终发表和安全验证 |
| 本地到点正式发布 | 当前账号不可实现 | 需取得 `freepublish/submit` 权限 |
| 读取或批量删除已发布文章 | 当前账号不可实现 | 发布接口无权限 |
| 批量删除草稿 | 可实现 | 预览 manifest、二次确认、逐条 `draft/delete` |

## 每周 35 篇的实际流程

以每天 5 篇、连续 7 天为例：

1. 每周运行一次同步，读取公众号现有草稿并更新本地镜像。
2. 从尚未排期的草稿中选择下一批最多 35 篇，按 7 天 × 5 个时段生成 `scheduled_at`。
3. 通过草稿 API 更新可写字段，不创建重复草稿。
4. 为每篇生成外部 Agent 任务包，包含标题、`media_id`、目标草稿创建时间、固定合集、留言设置和核对清单。
5. 浏览器 Agent 在公众号后台逐篇设置合集、推荐/通知、封面显示和目标时间，保存后重新打开核验；微信要求的最终发表、扫码和手机确认由用户本人完成。
6. 每篇保存截图或后台状态作为 proof；只有存在 proof 才标记为已人工处理或已核对。
7. 下周从游标继续向后选取，排除已确认和已处理的草稿，避免重复。

推荐时段可继续使用当前规则，例如 `09:00 / 12:00 / 15:00 / 18:00 / 21:00`。最终应以公众号后台实际允许的时间间隔和每日数量为准。

## 状态修订

建议后续把“草稿准备”和“正式发布”拆开：

```text
imported
-> scheduled_local
-> remote_draft_ready
-> manual_backend_action_pending
-> manual_backend_action_confirmed
-> published_confirmed
```

- `remote_draft_ready`：API 草稿已准备好。
- `manual_backend_action_pending`：等待用户在后台处理发布/定时发布和 API 不支持字段。
- `manual_backend_action_confirmed`：已有截图或后台状态 proof。
- `published_confirmed`：只在人工确认、公开链接或将来可用的发布状态接口证明后写入。

当前账号不得从 `remote_draft_ready` 直接进入 `submitted`。

## 运行安全配置

当前账号应固定使用：

```bash
WECHAT_MODE=real
WECHAT_ENABLE_PUBLISH=false
```

项目可以联网管理真实草稿，但不得尝试 `freepublish/submit`。即使任务误选“正式发布”，工作台也应提示“账号发布接口无权限”，而不是承诺到点发布。

## 外部 Agent 要求

任务包必须明确：

- 使用用户已经登录的浏览器会话，不读取或导出 cookie。
- 不绕过扫码、验证码或平台风控。
- 精确匹配标题和 `media_id`，操作前后截图。
- 只定位、核对并记录任务指定的合集、留言、推荐/通知、封面和时间等人工事项。
- 发现平台限额、账号警告或页面结构变化时立即停止。
- 可在本批次获得明确批准后推进到安全验证节点；出现二维码、管理员确认或手机确认时立即停止，由用户本人完成。
- 不读取、解析、复用或绕过二维码，不隐藏自动化控制状态，不修改请求绕过平台验证。
- 若每篇都触发安全验证，只能采用“Agent 填写 → 用户验证 → Agent 核验”的半自动模式，不能承诺无人值守。

`wechat-chrome-session` 已验证可以连接用户现有的已登录公众号页面。当前实际阻塞来自微信对发布/定时等风险操作的管理员扫码或手机确认，不是本仓库权限，也不能通过修改本仓库解除。

## 后续实现顺序

1. 在工作台增加“当前账号：草稿 API 可用 / 发布 API 无权限”的固定能力档案。
2. 固定禁用“自动正式发布”和 `freepublish/submit` 调度路径。
3. 增加 `manual_backend_action_pending` / `manual_backend_action_confirmed` 状态与 proof。
4. 增加每周批量任务包清单，一个清单覆盖 35 篇，而不只生成零散目录。
5. 将推荐/通知、封面显示、固定合集和后台时间写入任务包目标字段，作为人工处理清单。
6. 增加外部 Agent 执行结果导入、失败续跑和页面变化告警。
7. 如果以后重新评估发布权限，也应作为单独人工确认能力设计；这仍不是微信后台定时字段。

## 官方依据

- [发布能力](https://developers.weixin.qq.com/doc/service/guide/product/publish.html)
- [`freepublish/submit`](https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_submit.html)
- [草稿箱能力](https://developers.weixin.qq.com/doc/service/guide/product/draft.html)
