# 微信能力矩阵

> 产品定位：本工具是个人本地微信公众号草稿排期工作台。Agent 可完成发布前字段设置和保存草稿；正式发表与平台安全验证由用户完成。

> 当前账号结论（2026-06-06）：草稿接口有权限；截图显示发布接口整组无权限。因此当前账号必须使用草稿-only，具体落地见 [`draft_only_account_execution_plan.md`](draft_only_account_execution_plan.md)。

| 能力 | 当前状态 | 模式 | 说明 |
|------|---------|------|------|
| token 获取与缓存 | 已实现 | real | `TokenCache` 内存缓存，不落盘 |
| 网页批量上传作品与封面 | 已实现 | all | `POST /api/upload`，封面按文件名绑定，每篇可单独换封面 |
| 每篇作品独立封面 | 已实现 | real/mock | `articles.cover_path`，real 优先用该封面，回退默认 thumb |
| 封面素材上传 | 已实现 | real | `material/add_material`，按封面路径缓存 media_id |
| 草稿创建 | 已实现 | real/mock | real 调 `draft/add`，mock 本地生成 |
| 草稿更新 | 已实现 | real/mock | real 调 `draft/update`；内容指纹幂等；旧记录 `superseded` 保留 |
| 发布提交 | 人工最终动作 | browser | Agent 准备并保存草稿；用户最终发表并完成安全验证 |
| 草稿创建安全闸门 | 已实现 | real/mock | 默认 mock 不联网；real 模式只创建/更新草稿；执行到点前做草稿创建前检查（**已移除审核闸门**） |
| 本地草稿创建排期 | 已实现 | real/mock | 本地 scheduler 到点调用草稿 API 或 mock，按时把文章送入草稿箱 |
| 微信后台定时发布字段 | 浏览器辅助 | browser | Agent 可填写目标时间并保存；须实机验证时间是否随草稿持久化 |
| 扫描/排期/执行 CLI | 已实现 | all | 本地闭环保留，上传内部复用 scan |
| Web 工作台 | 已实现 | all | 作品库网格、上传、定时 UX、预检清单 |
| Web 草稿排期 UX | 已实现 | all | 人话计划草稿创建时间与下一篇摘要 |
| 真实发布预检 | 已实现 | real | `/api/publish-preflight` 本地检查（模式/封面/摘要） |
| 内容审核 / review_status | 已移除 | n/a | Round 43 产品重定位移除，不再有审核步骤 |
| 完整封面裁剪流程 | 暂不做 | n/a | 仅上传与绑定，不做在线裁剪 |
| 项目内网页登录自动化 | 禁止 | n/a | 不保存 cookie、不绕过登录；只导出外部 Agent 任务包 |

## 字段级能力矩阵

> 机器可读来源：`src/wechat_article_scheduler/wechat_field_matrix.py`（`GET /api/wechat-field-matrix`）。**未核验**项不得当作已支持；缺口处理以 `handling` 列为准。

| 字段 ID | 名称 | API 支持 | 本仓库实现 | 缺口 | 处理方式 |
|---------|------|----------|------------|------|----------|
| title | 标题 | supported | yes | 无 | draft/add、draft/update |
| digest | 摘要 | supported | yes | 超 120 字截断 | clamp_summary + 事件 |
| body | 正文 HTML | supported | yes | 标题重复/HTML 需预检 | render_for_publish |
| author | 作者 | supported | yes | 无 | PublishConfig → DraftOptions |
| content_source_url | 原文链接 | supported | yes | 无 | 任务级配置 |
| need_open_comment | 开启留言 | supported | yes | 无 | 草稿字段 |
| only_fans_can_comment | 仅粉丝留言 | supported | yes | 需先开启留言 | 草稿字段 |
| cover_thumb | 封面素材 | supported | yes | 缺省用默认图 | material/add_material |
| cover_crop | 封面裁剪 | unverified | partial | API 映射未确认 | 本地 cover_config；人工核对 |
| local_schedule | 本地草稿创建排期 | n/a | yes | 非微信字段，不写入微信后台时间 | publish_jobs + scheduler |
| wechat_backend_schedule | 后台定时发布 | unsupported | partial | API 无时间参数，保存持久化需实机核验 | Agent 填写并保存草稿；用户最终发表 |
| draft_create | 草稿创建 | supported | yes | 无 | draft/add |
| draft_update | 草稿更新 | supported | yes | 需已有 media_id | draft/update |
| freepublish | API 正式发布 | supported | no | 当前产品目标放弃自动正式发布；当前账号无权限 | 不在自动化范围；用户后台人工发布 |
| show_cover_pic | 正文内显示封面 | unverified | no | 未接线 | 待核验 |

### 字段缺口摘要

- **API 明确不支持**：`wechat_backend_schedule` — 草稿 API 与官方发布接口都不能写后台定时时间。
- **待核验 API**：`cover_crop`、`show_cover_pic` — 不对外声称已支持。
- **当前账号不可用**：发布、发布状态、已发布列表和已发布删除。
- **后台交接**：Agent 设置固定合集、推荐/通知、封面和目标时间并保存草稿；用户只负责最终发表、安全验证及必要的时间回填。
- **部分实现**：封面裁剪仅存本地 JSON，草稿创建后请在后台确认视觉效果。
