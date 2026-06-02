# 微信能力矩阵

> 产品定位：本工具是个人本地微信公众号发布工作台，**没有"审核"步骤**。默认 `WECHAT_MODE=mock` 不联网；显式切到 `WECHAT_MODE=real` 后进入真实 API 测试模式；需要草稿-only 时设置 `WECHAT_ENABLE_PUBLISH=false`。

| 能力 | 当前状态 | 模式 | 说明 |
|------|---------|------|------|
| token 获取与缓存 | 已实现 | real | `TokenCache` 内存缓存，不落盘 |
| 网页批量上传作品与封面 | 已实现 | all | `POST /api/upload`，封面按文件名绑定，每篇可单独换封面 |
| 每篇作品独立封面 | 已实现 | real/mock | `articles.cover_path`，real 优先用该封面，回退默认 thumb |
| 封面素材上传 | 已实现 | real | `material/add_material`，按封面路径缓存 media_id |
| 草稿创建 | 已实现 | real/mock | real 调 `draft/add`，mock 本地生成 |
| 草稿更新 | 已实现 | real/mock | real 调 `draft/update`；内容指纹幂等；旧记录 `superseded` 保留 |
| 发布提交 | 已实现 | real/mock | 受 `WECHAT_ENABLE_PUBLISH` 控制 |
| 发布安全闸门 | 已实现 | real | 默认 mock 不联网；real 模式用于真实 API 测试；任务级“仅草稿”不发布；执行到点前二次确认（**已移除审核闸门**） |
| 本地定时发布 | 已实现 | real/mock | `publish_jobs.scheduled_at` + 本地 scheduler 到点调用 API |
| 微信后台定时群发字段 | 待核验 | browser_assist fallback | 当前代码没有把发布时间写入微信后台草稿箱；若官方 API 不支持，走 browser_assist + 人工确认 |
| 扫描/排期/执行 CLI | 已实现 | all | 本地闭环保留，上传内部复用 scan |
| Web 工作台 | 已实现 | all | 作品库网格、上传、定时 UX、预检清单 |
| Web 定时发布 UX | 已实现 | all | 人话计划时间与下一篇摘要 |
| 真实发布预检 | 已实现 | real | `/api/publish-preflight` 本地检查（模式/封面/摘要） |
| 内容审核 / review_status | 已移除 | n/a | Round 43 产品重定位移除，不再有审核步骤 |
| 完整封面裁剪流程 | 暂不做 | n/a | 仅上传与绑定，不做在线裁剪 |
| 网页登录后台自动化 | 禁止 | n/a | 安全边界：不模拟后台登录 |

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
| local_schedule | 本地排期 | n/a | yes | 非微信字段 | publish_jobs + scheduler |
| wechat_backend_schedule | 后台定时群发 | unverified | no | 未写入后台 | browser_assist 后备 |
| draft_create | 草稿创建 | supported | yes | 无 | draft/add |
| draft_update | 草稿更新 | supported | yes | 需已有 media_id | draft/update |
| freepublish | 正式发布 | supported | yes | 受发布开关限制 | freepublish/submit |
| show_cover_pic | 正文内显示封面 | unverified | no | 未接线 | 待核验 |

### 字段缺口摘要（Round 72）

- **待核验 API**：`cover_crop`、`wechat_backend_schedule`、`show_cover_pic` — 不对外声称已支持。
- **明确未实现**：公众号后台定时 — 当前仅本地到点；见 `docs/wechat_browser_assist_strategy.md`。
- **部分实现**：封面裁剪仅存本地 JSON，发布前请在后台确认视觉效果。
