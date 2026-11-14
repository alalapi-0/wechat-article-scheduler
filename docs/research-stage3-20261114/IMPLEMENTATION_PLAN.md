# 微信公众号草稿工作台：复用既有草稿链路，补齐只读核对与权限诊断边界

任务：personal-account-tools-stage2-wechat-mp / personal-account-tools-stage2-wechat-mp-v1
目标：wechat-article-scheduler（目标仓库）
目标版本：5c476e4c66905867358fa8483ed08a01181271d6
输入标识：e47ac454264d20281b2597093c39a4c8b9df99e021f9220c282ac5f319f2a0ae

本交付仅为实施计划；未执行目标业务代码、安装依赖或启动集成。

## 当前问题

- 现有适配器已实现 token、封面永久素材、草稿创建/更新、草稿和已发表列表，不应重建这些能力；缺少的是按已知 media_id 单篇只读回看，以及能明确区分凭证、IP 白名单和端点权限的诊断。
- capability_probe.py 把 48001 与若干 token/凭证错误合并标为接口未授权；wechat_errors.py 对 42001 提示自动刷新重试，而本次核对的 HTTP 和 TokenCache 实现只有缓存到期刷新，没有该错误触发的重试机制。现有提示可能让调用者误判恢复动作。
- 本地草稿复用依赖成功记录、内容指纹以及任务/草稿的 mock/real 来源一致性，不能证明丢失创建响应时远端没有草稿；当前只读列表镜像也不是单篇内容一致性证明。未核对的调度调用链和不确定状态处理，不能据此宣布缺失。
- 外部 Chrome 只读协作已经有运行手册，但 host 匹配和选中标签不能单独证明当前页面属于指定账号、草稿和任务；来源发现的失效后回退第一页行为需要在该手册中明确禁止作为继续核对的依据。

## 研究依据与适用条件

- [source_fact] MP1 已有证据支持素材、draft add/update/get/batchget 及发表只读接口的字段契约；SDK 的接口存在、字段结构化程度与真实账号当前权限是不同结论。来源的发表提交和草稿删除接口不构成本项目采用授权。；条件：仅使用正式 stage2 的 MP1 章节及其固定来源和官方补证，研究 answered 不表示账号实测、实现完成或平台授权。；证据：stage2
- [source_fact] 官方发表状态回读与固定 SDK 存在字段差异：publish_id 的字段表、示例和请求类型不完全一致，msg_data_id 的官方 string 与 CLI int64 不能混同；成功需要原 publish_status、article_id 和 article_detail.item 中的 idx/article_url，fail_idx 出现不能单独判断终态。；条件：若以后单独启用只读发表状态查询，必须由可信外部输入提供真实 publish_id，保留标识符原值和原状态；不由草稿 media_id、article_id 或标题猜造标识，也不自动提交发表以取得标识。；证据：stage2
- [source_fact] 40164、40243、40125 和 48001 分别涉及 IP 白名单、AppSecret 冻结、secret 不合法及端点未授权；发表权限声明不能反推草稿、素材或当前账号权限。SDK 的令牌刷新重发也不是写操作幂等保证。；条件：这些是已接收研究的官方契约和来源行为；实际账号类型、认证状态和当前授权仍待所有者在单独授权的 real 检查中核实。；证据：stage2
- [source_fact] BR1 的 pageId、URL/type、扩展 attachedTabs 和持久 profile 各有作用，但不构成统一账号或任务授权；选中页失效可能回退第一页，固定客户端版本与实际页面行为仍需另行验证。；条件：本项目只采用外部只读协作的显式选择、身份复核和版本记录规范，不采用来源中的内置浏览器、会话存储或 stealth 行为。；证据：stage2:personal-account-tools-stage2-shared
- [target_hypothesis] 沿现有可注入 HTTP 的适配器补充 draft/get，并在现有 remote_sync 模块提供独立单篇核对入口，可以增加只读证据而不改变草稿创建、更新、排期和最终 proof 的语义。；条件：这是拟实施方案；单篇核对不能解决未知 media_id 的创建超时，不自动改任务成功状态，也不代替真实账号或人工内容验收。；证据：stage2

## 与既有计划的关系

new：正式请求没有绑定现行实施计划。以现行源码和项目规则为基线提出三个小任务；docs/backlog.md 的未来方向保持待决性质，不将旧预研或历史计划恢复为执行授权。
沿用目标约定：保留个人本地公众号草稿工作台定位、默认 WECHAT_MODE=mock、SQLite/src layout、现有 CLI 和 storage_runtime.py 隔离入口。现有 docs/backlog.md 明确不是路线图，request 未绑定任何现行编号实施计划；本计划新设 WAS-RS3-01 至 WAS-RS3-03，只表示本轮候选任务编号。业务唯一状态仍沿既有 project.yaml，未来实施前定点读取，不在研究项目建立第二份执行状态。真实模式只允许 token、素材、草稿创建/更新和只读同步；最终发布由用户在后台完成，实际 proof 与浏览器检查报告分离。实施时遵守 AGENTS.md 的 apply_patch、隔离测试及用户数据保护约定；本轮不执行任何目标命令。

## 采用、暂缓和不采用

- adopt：复用现有 token、封面上传、draft add/update、两个 batchget、同模式同指纹复用和分页镜像，增量补充已知 media_id 的 draft/get 只读核对。；理由：这些能力已在当前真实文件确认存在；单篇读接口在所核对的适配器和基类中不存在，且与当前草稿工作台目标直接相关。；证据：stage2, target:src/wechat_article_scheduler/adapters/real.py, target:src/wechat_article_scheduler/adapters/base.py, target:src/wechat_article_scheduler/remote_sync.py, target:src/wechat_article_scheduler/scheduler/draft_idempotency.py
- adopt：沿用既有端点探测与缓存，将接口未授权、认证/凭证问题、IP 白名单、限流和其他请求失败分开解释；保持草稿列表与已发表列表的能力结果独立。；理由：已有探测框架，不需要另建账号系统或第二套能力注册。只读发表探测失败不应被提升为整个工作台或草稿能力不可用；当前 remote_sync 已仅按 draft_probe 决定草稿同步阻断，该行为应保留。；证据：stage2, target:src/wechat_article_scheduler/capability_probe.py, target:src/wechat_article_scheduler/wechat_errors.py, target:src/wechat_article_scheduler/adapters/wechat_http.py, target:src/wechat_article_scheduler/remote_sync.py
- adopt：在现有外部只读 Chrome 手册中补充显式页面句柄、可见账号与任务草稿匹配、每次核对前重新确认页面和固定客户端版本记录。；理由：现有手册和产品边界已经覆盖外部连接与检查报告；需要收紧页面失效和账号不明时的停止条件，无须引入浏览器依赖或运行时。；证据：stage2:personal-account-tools-stage2-shared, target:docs/wechat_chrome_session_runbook.md, target:README.md, target:AGENTS.md
- defer：暂不把 freepublish/get、freepublish/getarticle 及发表状态结构化接成当前运行时功能；保留明确字段方案和重新准入条件。；理由：所核对真实适配器只有已发表 batchget；当前产品没有已确认的可信外部 publish_id 交付路径，也不允许通过自动提交取得它。未来若所有者明确要求只读查询且能提供适用标识，可单独增加纯只读契约：状态 0 才解析成功文章与 URL，1 为处理中，2/3/4 为相应失败，5/6 保留删除/封禁事实，未知状态和 fail_idx 均保留，不转为 proof。其权限未知不阻塞本轮 mock、草稿读写或 draft/get 实施。；证据：stage2, target:src/wechat_article_scheduler/adapters/real.py, target:README.md, target:AGENTS.md
- defer：临时素材 upload/get、正文图 uploadimg 及更广泛永久素材类型暂不扩入适配器。；理由：当前适配器封面永久素材已服务既有草稿链路；本次没有证明其他素材端点是当前输入或核对流程的必要条件。正文图适配可随 backlog 中的排版/预览一致性独立准入，不因上游支持就扩大范围。；证据：stage2, target:src/wechat_article_scheduler/adapters/real.py, target:docs/backlog.md
- reject：不采用 freepublish/submit、draft/delete、自动发布、远端删除、群发、最终定时确认、MP2 互动能力及其他平台运行时。；理由：这些能力不在本接收项目的 MP1/BR1 授权边界内，且若干操作被现行 AGENTS.md 明确禁止。接口文档和研究 answered 不能改变产品边界。；证据：stage2, target:AGENTS.md, target:README.md, target:docs/backlog.md
- reject：不以令牌刷新、草稿标题匹配、空列表或自动重建草稿解决不确定写入，也不把外部截图、连接报告或只读状态查询自动变为发布 proof。；理由：现有指纹复用依赖已保存记录；只读列表与页面选择没有证明所有副作用、账号身份和人工最终动作。未经核对的调度模块只列实施前定点核查，不宣称其现有处理不存在。；证据：stage2, stage2:personal-account-tools-stage2-shared, target:src/wechat_article_scheduler/scheduler/draft_idempotency.py, target:docs/wechat_chrome_session_runbook.md, target:README.md

## 可复用能力

- 真实草稿创建和更新：保留 RealWechatAdapter.create_draft/update_draft、_build_article_fields 和 DraftResult；不重写 articles、media_id/index/articles 请求格式，不改变现有留言开关默认值，也不把 MP2 接口引入当前项目。；证据：target:src/wechat_article_scheduler/adapters/real.py, target:src/wechat_article_scheduler/adapters/base.py
- 令牌、封面和可测试 HTTP：复用 TokenCache 的内存缓存、redact_url、可注入 HTTP 函数、受管封面读取和封面字节摘要缓存；任何新读接口都复用现有 token 获取，不新增落盘凭据或依赖。；证据：target:src/wechat_article_scheduler/adapters/wechat_http.py, target:src/wechat_article_scheduler/adapters/real.py
- 已保存草稿的同内容同模式幂等复用：保留 find_reusable_draft_media_id 对 article、content_fingerprint、mock/real、任务关联及成功状态的约束和 draft_result_from_reuse；单篇只读结果不自行放宽条件，不称为跨账号幂等或创建超时恢复保证。；证据：target:src/wechat_article_scheduler/scheduler/draft_idempotency.py, target:src/wechat_article_scheduler/adapters/real.py
- 草稿分页只读镜像：复用 sync_remote_drafts、upsert_remote_mirror 及现有表；保留 max_pages 截断时不标 stale、完整扫描后才更新本地 stale 标记的行为。stale 只表示本地镜像状态，不调用远端删除。；证据：target:src/wechat_article_scheduler/remote_sync.py
- 端点级能力探测和缓存：沿 probe_draft_batchget/probe_freepublish_batchget/probe_all_capabilities、wechat_capability_cache 和 human_capability_summary 增量修正原因分类；保留 authorized/empty/unauthorized/error 的既有外层 state，避免另建权限状态机。；证据：target:src/wechat_article_scheduler/capability_probe.py, target:src/wechat_article_scheduler/remote_sync.py
- 外部浏览器只读协作与人工 proof 边界：复用现有 export-agent-task 流程的文档契约和 Chrome 只读手册；项目自身不启动浏览器、不存储 profile/cookie、不实现会话状态机。已有说明已经区分检查报告与实际 proof，本轮只补页面和账号核对要求。；证据：target:README.md, target:docs/wechat_chrome_session_runbook.md, target:AGENTS.md

## 实施顺序与验收

### WAS-RS3-01 · 既有权限诊断的有界修正

依赖：无
路径：src/wechat_article_scheduler/capability_probe.py, src/wechat_article_scheduler/wechat_errors.py, src/wechat_article_scheduler/adapters/wechat_http.py, src/wechat_article_scheduler/remote_sync.py
调整：复用 _classify_probe_response 及原探测/缓存函数，只有明确的 48001 才解释为该端点未授权；token/凭证问题、40164、40243、40125、限流和其他错误保留原错误码并给出不同原因。保留原外层 state 与字段；可在结果和已有 raw_redacted 内增补 reason_code/action_hint，不增加凭据或新的缓存表。修正 42001 的自动重试提示，使提示与真实实现一致。
接口与数据流：WechatApiError.errcode/endpoint → 统一的安全错误解释 → _classify_probe_response → 原 draft_list/published_list 结果 → 原 cache_capability_probe/get_cached_capabilities/human_capability_summary。新增原因分类是附加信息，不能让 published_list 的失败覆盖 draft_list。
预期行为：空列表继续表示该端点在本次观察可读取且无内容；token 成功只证明此次 token 获取，不证明账号类型或所有接口授权。缓存保持带 probed_at 的历史观察，不能当作当前账号权利证明。草稿列表可读且已发表列表 48001 时，草稿同步继续；真实凭据或白名单问题明确交由用户处理，不自动重放写请求。
验证：未来实施时扩展既有能力探测/HTTP 单元测试，使用注入的合成响应覆盖非空与空列表、48001、40164、40243、40125、token 错误、限流、网络失败以及草稿可读但发表未授权。确认 HTTP 调用次数不会因新增提示重试 create/update。按 AGENTS.md 运行 python3 -I -B scripts/storage_runtime.py test，再运行 python3 -I -B scripts/test_linux_profile.py current；本规划轮不执行。
验收：保留原探测接口和外层 state，所有新增原因测试通过；没有把 token/凭证错误写成确定的接口权限结论；发表列表失败不新增草稿阻断；mock 保持无网络且未新增测试失败；42001 不再承诺未实现的自动恢复。
迁移：不变更 SQLite 表结构、不读取或重写用户旧数据；已有缓存行仍可读取，新诊断字段可缺省，旧行只作为历史观察展示。若实现需改变缓存 schema，必须先定点核对现有 db/migrations 并重新提出受控迁移，不在本步骤中猜测迁移编号。
回退：按本步骤的精确代码差异回退原因分类和附加字段；原缓存表及历史记录保留，旧调用者仍按原 state 工作。不回滚用户任务、文章或凭据。
当前代码证据：target:src/wechat_article_scheduler/capability_probe.py, target:src/wechat_article_scheduler/wechat_errors.py, target:src/wechat_article_scheduler/adapters/wechat_http.py, target:src/wechat_article_scheduler/remote_sync.py
研究证据：stage2

### WAS-RS3-02 · 已知草稿的单篇只读核对

依赖：WAS-RS3-01
路径：src/wechat_article_scheduler/adapters/base.py, src/wechat_article_scheduler/adapters/real.py, src/wechat_article_scheduler/remote_sync.py
调整：在 WechatAdapter 增加非 abstract 的可选 get_draft(*, media_id: str) 接口，默认明确 NotImplementedError，避免使当前 mock 子类无法实例化；RealWechatAdapter 通过既有可注入 HTTP 调用 draft/get。remote_sync 增加独立 inspect_known_draft(config, *, media_id, index=0, expected_fields=None) 只读核对函数，返回所请求标识、可读取性、字段差异及核对结论；不新增自动任务或数据库成功投影。
接口与数据流：调用方提供有来源的 media_id、文章 index 及可选预期公开字段 → inspect_known_draft → get_adapter → get_draft → draft/get 的 news_item 响应 → readable/mismatch/missing/unsupported/error 只读结果。比较 title/digest/content/thumb_media_id 等字段时保留缺失与未知；没有 expected_fields 只能报告已读取，不能声称内容一致。不得调用会上传封面的 _build_article_fields 来构造只读预期值。
预期行为：本步骤只为已知标识增加回看证据。空标识在联网前拒绝；mock 未实现可选读接口时返回明确 unsupported，原导入/排期/建草稿演练继续；61452/61453 保留草稿缺失事实，不删除远端或自动创建替代草稿。单篇读取不把本地 title/update_time 镜像摘要当作正文指纹，不放宽现有草稿复用条件，也不把读取成功改成任务成功或发布 proof。
验证：未来使用合成 HTTP fixtures 验证正确请求只有 media_id、返回多篇 news_item 时 index 选择、字段缺失、正文差异、缺失草稿、未授权、网络中断、空标识以及 mock/不支持适配器；用计数型 fake 明确断言检查不调用素材上传、create_draft 或 update_draft，且不修改 SQLite。复用既有幂等和同步回归验证，保留跨模式拒绝、max_pages 截断不标 stale、完整扫描才标 stale。按项目规定运行隔离 Python 测试和完整 current profile；本轮未运行。
验收：get_draft 在注入 HTTP 下按正确端点和字段请求；只读结果区分读取成功、内容匹配、差异、未知与不支持。既有 mock 子类仍可实例化，默认不联网。已知 media_id 的核对可用，但未知创建结果仍明确不能凭此消除；没有增加写重试、远端删除、发布调用、proof 生成或调度状态变更。
迁移：仅新增兼容的非 abstract 方法和只读函数，不变更 DraftResult、已有任务/草稿行、数据库 schema 或指纹算法。接入现有 CLI/Web/调度状态不是本步骤的隐含范围；若后续要求接入，先定点核对其真实调用点和现有不确定效果处理，再扩充执行范围。
回退：移除新增只读函数和可选方法，保留原 add/update/batchget、缓存和所有本地数据。该检查不产生远端修改，无需也不得以删除远端草稿补偿。
当前代码证据：target:src/wechat_article_scheduler/adapters/base.py, target:src/wechat_article_scheduler/adapters/real.py, target:src/wechat_article_scheduler/remote_sync.py, target:src/wechat_article_scheduler/scheduler/draft_idempotency.py
研究证据：stage2

### WAS-RS3-03 · 外部只读协作与未采用能力交接

依赖：无
路径：docs/wechat_chrome_session_runbook.md, README.md, docs/backlog.md
调整：在现有只读连接和任务包核对章节中补充显式页面句柄、可见账号与目标草稿身份、每次快照/截图前重新核对和所选页失效即停止；不得依赖第一页、当前页、host 或标题单项匹配继续。记录实际外部客户端/连接方式和固定版本，不用 @latest 作为稳定验收身份。README 只说明新增只读接口的能力边界；backlog 仍只记录暂缓能力、原因及重新准入条件。
接口与数据流：既有 export-agent-task 的 task.json/checklist.md → 用户授权的外部连接器 → 显式目标页和可见账号/草稿核对 → 脱敏只读检查报告。补充报告只含版本、页面身份已确认/未知、账号匹配已确认/未知、任务匹配及停止原因，不含 cookie、token、完整带参数 URL 或会话文件。检查报告仍不进入发布 proof 成功路径。
预期行为：账号身份不明、多个候选页、页面关闭/替换、回退、登录/验证/风控均停止并交还用户；不得接管无关标签或保存草稿。freepublish/get/getarticle、其他素材端点和内置浏览器暂缓；发表提交/远端删除继续拒绝。任何发表权限未知均不能让本地 mock 或既有草稿功能被文档写成不可用。
验证：未来实施只运行文档/结构验证 python3 -I -B scripts/storage_runtime.py contract、链接与命令检查、git diff --check，并核对 README/手册/backlog 相互一致。用静态核对清单覆盖多账号页面、句柄失效回退、仅host匹配、版本未知以及检查报告不能充当 proof；不为文档修改启动浏览器。真实外部连接演练仅在用户另行授权后进行，其未验收不伪装为已通过。
验收：现有外部只读流程保留，停止条件明确覆盖页面失效与账号不明；没有新增项目浏览器运行时、登录态存储或多平台入口；文档明确区分已实现复用、拟补只读核对、暂缓发表状态能力和禁止动作。静态合同通过只能标文档验收，不能标真实浏览器或真实账号验收。
迁移：仅修改现有文档，无浏览器配置、profile、凭据或项目状态迁移；不改变 task.json 的实际格式，也不猜测未读取的导出器实现。若未来需变更任务包 schema，先另行定点核对并绑定对应源码。
回退：回退本步骤的文档差异即可；保留原有只读边界和所有用户任务包、浏览器会话与 proof，不清理用户标签页。
当前代码证据：target:docs/wechat_chrome_session_runbook.md, target:README.md, target:docs/backlog.md, target:AGENTS.md
研究证据：stage2, stage2:personal-account-tools-stage2-shared

## 报告与当前代码差异

- MP1 将原问题所列 token、封面、草稿 add/update 和两个 batchget 保留为目标未读假设；当前真实适配器已逐项确认这些能力存在。；处理：全部列 reuse；不把研究尚未读目标的谨慎措辞继续当作功能缺失。；证据：stage2, target:src/wechat_article_scheduler/adapters/real.py
- 研究指出尚未确认目标账号权限；当前源码已经有草稿/已发表列表的独立只读探测、空列表区分及缓存，但并非逐账号权限矩阵。；处理：复用探测，只修正错误解释并保留端点级和时间边界；账号类型、当前配置与凭据由单独 real 前置核验，不创建多账号系统或以 token 成功推断所有权限。；证据：stage2, target:src/wechat_article_scheduler/capability_probe.py, target:src/wechat_article_scheduler/remote_sync.py
- 目标提示 42001 将自动刷新后重试；当前所核对 TokenCache 仅按时间刷新，HTTP 对非零 errcode 直接抛 WechatApiError，没有该错误触发的刷新重试。来源 SDK 的自动重发不能作为本项目已有实现证据。；处理：WAS-RS3-01 修正提示和诊断；不顺带为草稿写接口加入自动重试。；证据：stage2, target:src/wechat_article_scheduler/wechat_errors.py, target:src/wechat_article_scheduler/adapters/wechat_http.py
- MP1 列出的 draft/get、freepublish/get/getarticle 候选缺口中，当前基类和真实适配器确实未提供这些方法；但这不能扩写为全仓不存在相关逻辑。；处理：本轮 adopt 已知 media_id 的草稿只读核对；发表状态及已发表单篇接口明确 defer，不能为取得 publish_id 反向采用提交接口。；证据：stage2, target:src/wechat_article_scheduler/adapters/base.py, target:src/wechat_article_scheduler/adapters/real.py
- 来源已给出发表状态与标识字段差异，目标当前只有 freepublish/batchget；不能把已有列表适配说成已具备 publish_id 到 article_id/URL 的状态链。；处理：保留为独立待准入的只读能力。重启条件是明确产品用途、可信外部标识及独立权限验证；届时保留官方/SDK类型差异和状态原值，不伪造 msg_data_id、不自动证明已发表。；证据：stage2, target:src/wechat_article_scheduler/adapters/real.py, target:README.md
- BR1 来源提供多种浏览器与会话实现；目标明确没有内置浏览器，且已存在外部 Chrome 只读 runbook，不能把研究通用机制当作缺少的运行时。；处理：仅补现行手册的显式页面/账号/任务复核与版本记录；不安装来源组件、不复制 storage state、不新增 browser session 状态机。；证据：stage2:personal-account-tools-stage2-shared, target:docs/wechat_chrome_session_runbook.md, target:AGENTS.md

## 未确认前提

- 本轮为第三阶段候选计划，目标代码写入、测试和业务执行尚未获本候选授权。；核实：后续实施由所有者明确授权；承接者先读取目标现行 AGENTS.md、project.yaml 和对应工作区归属，核对当时基线与未提交改动。不能自动恢复旧 Goal、研究队列或运行任务。；实施前必须核实：True
- 当前 real 账号类型、认证、AppSecret 状态、出口 IP 白名单和各端点实际权限没有本轮运行证据。；核实：该前置只适用于真实联网动作：须另获当次 token/只读探测或明确草稿写入授权，由用户在本地提供凭据并核对当前账号，逐端点记录脱敏结果；不读受保护配置来代替用户确认。mock、离线单元测试和本计划的代码实施不依赖发表权限。；实施前必须核实：True
- 当前目标测试文件、mock 子类、CLI/Web 调用点、调度器不确定效果处理和数据库迁移实现未纳入本次有界正式阅读。；核实：实施前只对所改接口的既有测试与具体调用点做定点核对，按需扩充受控证据。不能据此宣称现有 uncertain 状态不存在、重建队列、修改 proof 或直接变更 schema；必要新增范围先确认授权。；实施前必须核实：True
- 只读单篇核对必须有可信来源的已知 media_id；创建响应丢失时这个前置可能不成立。；核实：调用方验证已有成功记录的任务/模式来源或用户明确提供的目标标识；缺失标识直接返回无法核对，不通过标题猜测，不自动重新创建。；实施前必须核实：True
- 外部浏览器当前连接器版本、账号页面和句柄归属未在本轮检查。；核实：该前置只适用于外部浏览器演练：用户另行授权并由其完成登录/调试批准；核对真实客户端版本和目标页面的可见账号与任务身份，任一不明即停止。文档静态交付不表示该演练完成。；实施前必须核实：True

## 后续交接

- 本计划只承接 MP1/BR1，三个候选步骤均未实施。未来经授权后按 WAS-RS3-01 → WAS-RS3-02 执行；WAS-RS3-03 可独立完成，主代理整合最终验收。
- 执行承接者沿目标既有 storage_runtime.py 和 test_linux_profile.py 隔离入口进行必要验证，不读取用户 .env、数据库、文章、日志、storage 或浏览器会话。新增测试产物只进入临时目录或既有忽略目录。
- 本轮未执行目标程序、测试、浏览器、API、账号操作或 Git 交付。后续交付沿目标当前 Git 授权，由主协调者处理；不得将本候选当作提交、推送或发布授权。
- 独立 real 检查须分开报告 token、素材/草稿、只读列表、单篇读取和可选发表查询的实际能力，不以一项结果推断另一项，不因发表未知阻塞 mock 或草稿链路。禁止自动发表、远端删除和自动 proof。
- freepublish/get/getarticle、其他素材能力和浏览器运行时保持暂缓/拒绝去向，不能在实现时默认扩入；MP2 及其他平台由原接收映射负责，本项目不承接。
- 完成标准区分代码和隔离测试、真实草稿或只读 API、外部浏览器以及人工最终发布/视觉核对。未执行、失败和跳过分别保留，不把研究完成或静态合同通过写成实际采用。

## 实际输入与边界

- stage1：已绑定研究报告（原始回执保存在研究管理项目）；SHA-256 491df282d0df412ef14b0ea34a00760c820a1bd0a9f1a995c519147e9f71e1e4
- stage2：已绑定研究报告（原始回执保存在研究管理项目）；SHA-256 160c1b75419489fa97706a3ff92a7b1bfa4a76eef237db6a20903e1841bf3dac
- stage2:personal-account-tools-stage2-shared：已绑定研究报告（原始回执保存在研究管理项目）；SHA-256 b70b532a5380033b5ed64d4b9f12b41effb033a4d4609fa5fc76af6306e50e93
- target:AGENTS.md：AGENTS.md；SHA-256 69e7dbe46eb190cfacb0e034b9c5aadf0fcbd33302656d4e43794f1ae9e940d7
- target:README.md：README.md；SHA-256 0df824c25b31e1f39f0fda080ad84282aa1356063aba3ce34d07b90dd6637f6d
- target:src/wechat_article_scheduler/adapters/real.py：src/wechat_article_scheduler/adapters/real.py；SHA-256 e85f7beb6347a94d3ae1b0c4e57d1fdf35933567d7a7edaa4faca2d0e6e72348
- target:src/wechat_article_scheduler/adapters/wechat_http.py：src/wechat_article_scheduler/adapters/wechat_http.py；SHA-256 7c377efb993e4dbb0f430a3a8daaa7dfbb3bc4e80673c897370a33f4768db632
- target:src/wechat_article_scheduler/wechat_errors.py：src/wechat_article_scheduler/wechat_errors.py；SHA-256 59d7bcefafd08bd33ec85d591f9d7e1069d0e83200fe3ce01542964594a3ade4
- target:src/wechat_article_scheduler/remote_sync.py：src/wechat_article_scheduler/remote_sync.py；SHA-256 bc61e6580445096fbed4be3bf699e939a0649b29ccd9cb2542e0e07bd55dc00a
- target:src/wechat_article_scheduler/scheduler/draft_idempotency.py：src/wechat_article_scheduler/scheduler/draft_idempotency.py；SHA-256 f57c49c5af9373677474b431e3956971be025d073dc3751c439537b211b4b1dc
- target:docs/backlog.md：docs/backlog.md；SHA-256 ceb520784a69e4492c8cfd0fe2eeff5f8eb6cc92226e3f445739afb058c6ef8f
- target:src/wechat_article_scheduler/capability_probe.py：src/wechat_article_scheduler/capability_probe.py；SHA-256 7800a262ccd87cbe48ba0952b96d9e72d511758843a6a45237d35cf845e13fe7
- target:src/wechat_article_scheduler/adapters/base.py：src/wechat_article_scheduler/adapters/base.py；SHA-256 b2068114e690e7564aa90362e6b23109aff79da7f2754c39a8cf59caaf45f51c
- target:docs/wechat_chrome_session_runbook.md：docs/wechat_chrome_session_runbook.md；SHA-256 847922747fb86451e41ecb75b4a603824f96b1c9c87ec1aac7db36fde1bfe350

研究门控：complete, complete, complete
模型执行：当前宿主会话原生路径；脚本不发起模型调用，不推断型号、Token、费用或底层推理切换。
未提供的文件、运行效果与全仓完整性不在本计划验收范围。
