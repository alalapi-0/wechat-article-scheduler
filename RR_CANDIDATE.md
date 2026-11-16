# wechat-article-scheduler RR 有界源码候选

## 当前源码治理与采用范围

本候选作为源码保存和交付，不代表已经安装、注册或采用生产RR。当前唯一业务状态仍为
`project.yaml`，原Stage3技术交付与真实微信、人工proof、Owner Chrome和RR采用分别核实。
本轮仅修候选迁移隔离、严格身份测试夹具和测试入口的私有文件范围；结果由该状态的治理尾段记录。

016原SQL字节保留在 `src/wechat_article_scheduler/rr_review/candidate_migrations/016_rr_feedback.sql`。
普通 `db.init_db` 与应用启动只发现已发布迁移，独占新合成fixture才显式应用016。
native readiness只读核对预期版本，不自动迁移。真实数据库的采用状态本轮未读取或修改。
私人PCH计划和私人提交链继续留本地，测试视图排除这两份计划。

当前本机验证使用原固定入口，保留全部失败、跳过和网络观察：

    python3 -I -B scripts/storage_runtime.py test
    python3 -I -B scripts/test_linux_profile.py current
    python3 -I -B scripts/storage_runtime.py contract

RR合成集成依赖独立B项目的现行严格Peer和解析器。该依赖是私有工程，不复制到本仓库，
也不声称这些本机身份/浏览器检查适用于任意公开runner。socket用项目Temp中的短独占目录，
原生产UID/GID、sealed FD、source绑定与拒绝检查不放宽。未执行原生身份发行、服务安装或真实业务。

## 历史阶段2：补齐浏览器反馈流程（2026-10-22）

以下记录保留当时的实现知识和失败事实；归档基线、路径、旧证据及“通过”不充作当前候选验收。

RR Root独立审阅阶段1的14份源码、摘要及桌面截图后，指出SSR缺少浏览器提交和查询入口。
阶段1的API/CLI合成检查不构成完整页面流程通过。本阶段在同一隔离源中补上反馈区、独立
反馈JS及显式资源映射，沿用原SQLite事务、Unix角色和Agent协议，不采用正式服务或原库。
阶段1索引、manifest、源码输入及通过/失败检查保留在evidence的phase1文件及原日志中，
不是当前候选的采用证明。当时精确文件与证据由归档CANDIDATE.json限定，不替代现行状态记录。

反馈区在每个SSR页面提供带标签的正文输入、最多两件明确选择的受限附件、固定内容预览、
确认保存、按原请求核对、按反馈编号查询/刷新。UUID、时间、页面、source和resource在检查
时固定，正文/来源/摘要在该页面的localStorage中保存以恢复核对，附件字节仅在RAM。
未知提交结果不会自动重发；重载后先手动按原ID查询。未找到后仍需本人明确重试，并要求
重新选择与原长度、SHA和类型一致的附件。来源变化拒绝提交但保留旧反馈上下文和只读查询。
状态来自项目持久回执；Agent已读/处理必须有匹配revision、正文和附件的ack及result。
结果均用textContent显示。没有SSE、截图采集、Cookie/历史访问或微信动作。

Root另复现AgentClient接受正文SHA匹配的跨项目记录。本阶段对read、ack、result和list成功
返回补上项目/反馈对象绑定；单独公开替身负例不访问真实socket、DB或身份。
新增JS和HTML模板进入source inputs；JS的SHA、MIME与GET路径逐一登记，源漂移拒绝503。
本阶段验证仅跑受影响HTTP/CLI、浏览器端到端/恢复/版本拒绝和Agent对象绑定负例；
未变化的6项原迁移/Web、FD和反馈事务检查复用阶段1证据。

读者：RR Root、指定项目维护者。更新触发：本候选源码、验证或采用结论变化。

当时单元是未采用的隔离候选，不是正式服务。历史基线为项目提交
`844d37da80fd60cd6c1b62914f24070b4fef4f80` 的受控源码归档。现有
`hub.connection.yaml`、`project.yaml`、`docs/pch-rebuild-20261020/`、`research/`
保持原状。没有读取受保护数据、配置、会话或凭据，也未运行草稿写入、调度、发布、删除。

历史隔离候选位于项目 `artifacts/rr-source-candidate-20261022`，临时编辑源只含受控归档与新增单元。
当时的浏览器和小于5MiB合成SQLite/Unix socket使用独占临时输出并收尾清理；这些历史路径
不成为当前本机调用入口。当前验证复用上文固定Linux profile及项目Temp。

## 产品与数据

本项目是微信公众号草稿工作台。候选复用 `build_article_detail`、`list_queue_jobs`
和现有文案/日期规则，提供服务端生成的作品首页、两篇文章详情、排期和演练草稿状态。
SSR数据来自 `fixture.PUBLIC_ARTICLES` 固定公开构造内容及全新合成数据库；选择ID仅为1、2。
`Snapshot` 必须明确选择公开fixture并核对文章内容，不能自动导出原库文章。
页面复用原工作台浅色/系统字体约定，仅使用显式登记的本项目反馈脚本，无第三方CDN、
抓取或业务修改按钮；文章与排期保持只读，反馈是明确提交到项目的独立审核意见。
正式采用其他数据必须重新明确选择并与原维护者串行，不由此候选授权。

manifest由实际源码+选择数据计算build_id，commit是归档基线，dirty=true。
每个页面/CSS均有独立id、SHA、长度、MIME和精确GET路径；只有一个只读数据路径。
反馈列出四类浏览器路径。`websocket=false`、`sse=false`，不支持SSE、HMR或通用代理。
`source-inputs.json`列出实际哈希输入；根身份、源文件增删/变化/链接异常会关闭响应。
没有把未跟踪业务改动谎报为干净HEAD。

## 反馈与进程

新增迁移016仅在新合成库验证。反馈、正文、来源、附件BLOB在原项目SQLite
同一事务中提交；设备+请求UUID唯一，原载荷确定性SHA相同返回200，新增201，冲突409。
附件类型、实际字节、大小、摘要都校验；失败回滚整个事务。返回同一feedback_id、revision、
accepted_at、payload/body摘要及持久状态。当前反馈不可原位编辑，revision固定1。
按请求、反馈与附件的查询绑定同一设备；未知对象404。正文/附件不进入预览缓存。
严格JSON拒绝重复键、浮点数、NaN、非法UTF-8及代理字符；multipart拒绝未知/重复字段及额外尾部。

`integration.attach_review` 是原FastAPI应用的显式lifespan钩子，RR的两个Unix
监听器与SQLite连接都属于原项目进程。它没有迁移或另起DB写进程。平台与Agent CLI
只走接口，不打开SQLite。默认 `create_app`、CLI与本地8080管理路由没有修改，也未映射它们。
候选没有安装入口或后台服务；调用钩子必须由原维护者在串行采用时明确完成。

正式Agent协议通过Owner1000、mode0600的独立 `agent.sock` 提供；浏览器socket拒绝Agent路径。
CLI `python -m wechat_article_scheduler.rr_review.agent_cli --socket SOCKET list|read|ack|result ...`
只连接项目进程。read输出原正文、来源、附件base64；ack先实际重读正文及全部附件字节，独立核SHA，
再提交revision和摘要。result要求已确认revision并幂等保存真实说明/引用，不执行反馈内容。
本次CLI处理说明明确为合成验证，不代表指定维护聊天已经读取过真实用户反馈。
分页走受保护CLI的 `list --state --after --limit`；内部使用Agent专用POST `/list`，不开放浏览器查询串。

## 身份供给与拒绝边界

生产绑定为project_id=wechat-article-scheduler，origin=
`https://rr-wechat-article-scheduler.invalid:9419`。
浏览器Unix路径固定 `/run/rr-projects/wechat-article-scheduler/browser.sock`；
同目录Agent路径 `agent.sock`，不会接受任意上游地址/端口。
生产目录由Root预置Owner1000/GID984、0750或2750（新socket需继承984），
browser.sock为1000:984/0660，Agent socket0600。程序不创建原生目录、不chown、不安装服务。
浏览器实际peer必须UID996/GID984，Agent peer必须UID1000；两端检查HTTP Host固定pch-rr.local。
浏览器HMAC绑定一次challenge、项目、origin、方法、完整路径、正文SHA、device摘要、UUID nonce、
最多30秒时窗；challenge绑定实际pid/uid/gid，重放拒绝。Origin如提供必须确切匹配。
管理页、Agent、未知方法、未知路由、路径逃逸、query、Cookie与转发身份头均拒绝。
每个响应是有长度的HTTP/1.1；错误不返回正文或秘密。

`identity.NativeKey` 只在项目Owner进程内连接 `/run/rr-project-keys/key.sock`，请求
schema1/project_id/recipient_uid=1000；验证provider真实996:984及目录/文件身份。
只接受恰好一个O_RDONLY、CLOEXEC、无链接、400、996:984、32—64B的完全封印memfd，
名称 `rr-project-browser-key`，并验证确切项目回包。B角色名称
`rrp-wechat-article-scheduler-auth-key` 仅是绑定名称，不从env/argv/普通文件读值。
每次供给复核通过项目自身RAM完成；Agent/测试没有读取生产角色值。
公开fixture供给使用固定公开字节及显式测试参数，不是生产身份/权限通过。

## 历史验证与现行采用界线

历史归档复现入口（仍只可在原隔离候选目录运行，不从共享源码树绕过）：

    python3 -I -B scripts/rr_candidate_check.py

既有专用解释器复用，不安装依赖。有效检查覆盖实际SSR/CSS/反馈JS、B现行manifest/HMAC/HTTP
解析器、错误身份/Origin/管理路径、反馈事务回滚/重开持久化/幂等/附件、真实CLI子进程
读取/ack/result，以及隔离Chrome桌面/390px导航/焦点/布局/console/network。
当时B只读基线为 `c81b19e8818baf0dcbbfa75faf9778aa622bba96`，不代表当前依赖版本。
浏览器用公开fixture route bridge；Unix连接的路径和测试UID被明确替换，不能当正式mTLS、UID996、
真实Owner日常Chrome、原生供给或真实Agent闭环。SSR页面为只读，无加载/危险操作交互，
不引入动画。接口错误与原Web空文章列表有检查；当前公开选择固定两篇文章，没有声称空页面浏览器验收。

证据目录保留最终与失败日志。首次打包的AppleDouble附带文件已识别并删除（196件）；
第二次发现并修复multipart额外尾部。浏览器曾遇长临时socket路径，改为登记的短落盘路径；
后遇测试Peer类型不符合B严格检查，改用B真实Peer类型。失败均保留，没有隐去或当作通过。
阶段2最终浏览器检查1项通过（耗时见feedback-final.xml），受影响HTTP/CLI及新Agent对象绑定负例2项的通过结果
复用同一运行源码下phase2-attempt3.xml；该次浏览器的唯一失败是将预期的查询404误归为
非预期console，最终已核对恰好一条对应原请求的404并保留完整日志。此前发现重载后测试
过早选择仍禁用的文件框，以及真实窄屏版本摘要溢出，分别修复等待和反馈区换行，保留失败。
原迁移/三个原Web检查共6项通过，后续RR变化不改变它们，复用原证据，不重复完整矩阵。
原有Starlette/httpx弃用警告保留，未安装依赖或扩展修复范围。

生产采用仍须由当前所有者与本项目维护责任串行确认原生供给、目录权限、schema及Agent接线。
016不得直接投进原库或共享自动迁移目录；当前源码隔离修复不授予采用权限。
历史阶段未发行身份、注册、commit、push或启动正式服务；当前源码Git交付按当前治理状态核实，
不继承为服务或身份采用。本轮不修改原服务、原库、原用户状态或其他任务文件。
