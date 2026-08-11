# 架构

## 定位

系统是单机、单用户、local-first 的微信公众号草稿工作台。FastAPI Web 与 CLI 复用同一套 Python 领域逻辑和 SQLite 数据库，没有独立前端构建、任务队列或远端服务。

运行主线：

    articles/inbox 或 Web 上传
                ↓
         parser + dedupe + scan
                ↓
             articles
                ↓
               plan
                ↓
          publish_jobs
                ↓
        run-once / scheduler
                ↓
       mock adapter 或 WeChat draft API
                ↓
          wechat_drafts + events
              ↙       ↘
   可选只读任务包     用户最终发布 + proof

## 组件

| 目录/模块 | 职责 |
|---|---|
| parser.py、scanner.py、dedupe.py | 文章解析、导入和去重 |
| plan.py、schedule_assign.py、weekly_plan.py | 本地排期 |
| scheduler/ | claim、重试、幂等、到点执行和健康检查 |
| adapters/mock.py | 无网络演练 |
| adapters/real.py、adapters/wechat_http.py | token、素材和草稿 API |
| renderers/、publish_body.py | 微信正文与摘要构造 |
| content_library/ | 多合集读取和排期 |
| remote_sync.py | 远端草稿的只读镜像同步 |
| external_agent/ | 生成脱敏浏览器任务包，不运行浏览器 |
| publish_proof.py | 记录用户提供的真实 proof |
| web/ | FastAPI 路由和原生 HTML/CSS/JavaScript 工作台 |

## 数据

新数据库的基线 schema 由 db.py 中的 SCHEMA_SQL 创建，随后按顺序应用 migrations/ 中的增量迁移。当前主流程使用 articles、publish_jobs、wechat_drafts、events、publish_proofs 和 remote_content_mirror 等表。每条草稿记录都保存 `adapter_mode` 和 `publish_job_id`；只有任务、文章与模式来源完全匹配时，草稿才可复用、更新或进入 proof 流程。旧数据无法确定来源时迁移为 `unknown` 并按失败关闭处理。历史迁移及其旧表是已有本地数据库的兼容契约，不能因运行时代码清理而删除。

articles/** 与 content/collections/** 是用户内容。data/、storage/、outbox/、reports/ 和 artifacts/ 是本地状态或生成物，不是代码源真相。

## 安全边界

- mock 是默认模式，不调用微信。
- real adapter 只实现草稿创建/更新、素材和只读列表能力。
- 排期任务固定保存创建时的模式；执行进程模式不匹配时在构造 adapter 或发起网络请求前拒绝运行。
- 代码中不存在 freepublish/submit；环境变量不能重新打开最终发布能力。
- real 草稿必须有真实有效封面，且封面检查发生在 HTTP 请求之前。
- 外部 Agent 任务包不含 AppSecret、token、cookie、密码或浏览器会话。
- 扫码、验证码、风控、草稿删除和最终发布只由用户在公众号后台人工完成；项目不提供对应远端删除或最终发布接口。

## 有意不采用

当前不保留多平台 adapter registry、manual export、内置 browser-assist 状态机、manifest/content-package 抽象、产品内 roadmap/gate API、auto-review 或 quick proof。这些抽象曾扩大维护面，却没有服务微信草稿主线。
