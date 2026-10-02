# wechat-article-scheduler

个人本地微信公众号草稿工作台：把本地文章导入、去重、排期，并在到点时创建或更新微信公众号草稿。

项目不会自动发布、群发或确认微信后台定时发布。最终动作始终由用户在公众号后台完成；代码中不提供 freepublish/submit 调用。

## 核心流程

    本地文章 → scan → plan → run-once / scheduler → 微信草稿
                                                   ├→ 可选只读任务包
                                                   └→ 用户最终发布 → proof

- 默认 WECHAT_MODE=mock，不联网，适合完整演练。
- WECHAT_MODE=real 仅用于真实 token、素材、草稿和只读同步接口。
- Web 工作台提供上传、文章列表、预览、排期、队列、草稿、回收站和事件记录。
- 外部 Agent 任务包只帮助定位、核对和截图；不包含密钥，也不授权最终发布。

多平台发布、内置浏览器 Agent、自动审核、视频/音频内容包和通用 outbox 不属于当前产品。未来方向只记录在 [docs/backlog.md](docs/backlog.md)。

## 当前存储与运行状态

唯一项目状态入口是 [project.yaml](project.yaml)。当前 Linux 入口使用新的隔离 mock profile，不读取旧 `.env`、用户文章或旧数据库。固定解释器与存储根由本机 ext4 身份守卫验证；环境或路径漂移时停止。数据根为 `/home/alalapi/ProjectData/wechat-article-scheduler/linux-local-profile/mock`。

    python3 -I -B scripts/storage_runtime.py check
    python3 -I -B scripts/storage_runtime.py cli init-db

当前 Linux 环境使用专属 Python 3.12 和经过哈希登记的兼容 wheel；已有环境不会被重建覆盖。恢复环境、保留范围和未验证项见 [存储维护](docs/storage_runtime.md)。旧数据与真实微信模式须另行选择，不能把新空库当成旧数据迁移结果。

.env、config/rules.yaml、data/、storage/、outbox/、reports/ 和 artifacts/ 是本地状态，不应提交。不要把 AppSecret、token、cookie 或浏览器会话写进仓库。

## 启动 Web 工作台

    python3 -I -B scripts/storage_runtime.py cli serve

默认地址是 http://127.0.0.1:8080/。管理页没有登录保护，只能绑定本机地址，不能暴露到公网。

## CLI 日常使用

把新演练文章放进 Linux 本地 profile 的 articles/inbox/，或直接在 Web 工作台上传，然后执行：

    python3 -I -B scripts/storage_runtime.py cli scan
    python3 -I -B scripts/storage_runtime.py cli plan
    python3 -I -B scripts/storage_runtime.py cli run-once

常驻调度：

    python3 -I -B scripts/storage_runtime.py cli scheduler-health
    python3 -I -B scripts/storage_runtime.py cli scheduler-daemon

Web 默认会处理勾选了 auto_execute 的到期任务。Web 自动执行、scheduler-daemon 和 cron 只能选择一种；若使用 daemon 或 cron，请设置 WEB_AUTO_RUN_DUE=false，或不要同时运行 Web。

其他常用命令：

| 命令 | 用途 |
|---|---|
| sync-remote | 只读同步微信远端草稿镜像 |
| update-draft --article-id N | 更新已有微信草稿 |
| retry-failed | 将失败任务重置为待执行 |
| events --limit N | 查看本地审计事件 |
| content | 查看本地合集内容 |
| preview-snapshot --article-id N | 生成指定文章的本地预览快照 |
| cover-scan | 检查封面素材 |
| export-agent-task --job-id N | 导出一个外部 Agent 任务包 |
| export-agent-tasks --status draft_created | 批量导出任务包 |
| mark-waiting-confirmation --job-id N | 标记等待人工核对 |
| submit-proof --job-id N | 回填用户提供的真实 proof |

人工发布确认只适用于已经创建或复用真实微信草稿的 real 任务；mock 演练不能提交发布 proof 或把文章标为已发布。

每个排期任务都会保存创建当时的 `mock` 或 `real` 模式。执行进程的 `WECHAT_MODE` 与任务模式不一致时，任务会保持待执行并被拒绝运行；切换模式后需要在当前模式下重新安排该任务。已有草稿还必须带有匹配的任务和模式来源，旧数据中来源不明确的草稿不会被当作真实草稿复用、更新或提交 proof。

完整命令和参数以运行时帮助为准：

    python3 -I -B scripts/storage_runtime.py cli --help

## 真实草稿模式

以下是保留的旧数据维护说明，不属于当前 Linux mock 入口；本轮没有加载或验证此模式。Linux 专属环境已安装 python-dotenv，浏览器运行组件尚未验收；下方仓库内 `.venv` 命令属于历史说明，不能作为当前 Linux 入口使用。

在本地 .env 中设置：

    WECHAT_MODE=real
    WECHAT_APP_ID=...
    WECHAT_APP_SECRET=...
    WECHAT_DEFAULT_THUMB_PATH=/path/to/a/real/cover.jpg

real 模式需要可读取且非空的封面文件。可以给文章绑定独立封面，也可以设置真实默认封面；项目不再提供 1×1 占位封面。

只做安全 dry-run：

    .venv/bin/python scripts/real_api_check.py --dry-run --skip-if-blocked

显式真实草稿检查会联网并可能创建草稿，因此只在用户授权后运行：

    WECHAT_MODE=real .venv/bin/python scripts/real_api_check.py --samples 3

运行结果写入被 Git 忽略的 reports/real_api_runs/。脚本不调用最终发布接口。

## 外部浏览器协作

本项目本身不控制浏览器。export-agent-task 生成的目录包含 task.json、提示词、检查清单、文章预览和只读检查报告模板。外部工具或人工可以：

- 打开公众号后台并定位已创建草稿；
- 对比标题、摘要、正文、封面和合集；
- 截图、生成检查报告；
- 在最终发布按钮前停止。

只读检查报告不能作为发布 proof。发布 proof 只能在用户实际完成后台发布后单独回填。

不得绕过登录、扫码、验证码或风控，不得保存 cookie/密码，不得删除草稿或点击最终发布。可选的已登录 Chrome 只读连接说明见 [docs/wechat_chrome_session_runbook.md](docs/wechat_chrome_session_runbook.md)。

## 测试

    python3 -I -B scripts/storage_runtime.py test
    python3 -I -B scripts/storage_runtime.py contract

完整测试使用受控源码与合成 fixtures 的私有临时副本，保持测试断言，不复制旧配置、数据库或用户文章：

    python3 -I -B scripts/test_linux_profile.py current

浏览器不可用时，E2E 会按测试条件跳过。测试产物必须留在临时目录，不能污染仓库 outbox 或 tracked 报告。

## 文档

- [用户手册](docs/user_manual.md)
- [架构](docs/architecture.md)
- [微信能力矩阵](docs/wechat_capability_matrix.md)
- [Scheduler 手册](docs/scheduler_runbook.md)
- [测试说明](docs/testing/README.md)
- [文档索引](docs/index.md)

项目规则见 [AGENTS.md](AGENTS.md)。机器可读的项目身份见 [project.yaml](project.yaml)。
