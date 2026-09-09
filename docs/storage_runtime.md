# 外盘存储与运行

当前维护入口是 `python3 -B scripts/storage_runtime.py`。项目状态与此入口登记在 `project.yaml`；Hub 仅引用该状态，治理执行进度仍以 StorageGovernance/STATE.yaml 为准。

统一身份守卫通过后才使用 `/Volumes/AI_WORK_SSD` 下本项目的 Runtimes、ProjectData、Caches、Temp 根。运行解释器固定为外盘 CPython 3.11 虚拟环境；错盘、缺盘、目录别名、运行时缺失均退出 78，不创建内盘替代环境。

```sh
python3 -B scripts/storage_runtime.py check
python3 -B scripts/storage_runtime.py cli init-db
python3 -B scripts/storage_runtime.py cli serve --port 8080
python3 -B scripts/storage_runtime.py cli --help
python3 -B scripts/storage_runtime.py test
python3 -B scripts/storage_runtime.py contract
```

新默认 profile 为 `ProjectData/wechat-article-scheduler/mock/`。数据库、文章输入、日志、快照和输出都在此根，mock、dry-run、自动执行关闭、任务包导出关闭。它不加载仓库 `.env`、rules、文章、旧数据库或会话；这不是把历史数据自动导入新库。原库与用户的 `storage/README.md` 改动原样保留内盘。真实微信模式与旧数据恢复不在此次存储验证范围内，必须另行明确选择，不能把 mock 验证当成真实草稿验收。

离线环境由本机现有的 24 个兼容 wheel 展开包重建，清单在 `Runtimes/wechat-article-scheduler/offline_components.json`。虚拟环境不存在时可运行 `rebuild`；已有环境不会被覆盖，缺包不会联网下载。完整声明中的 python-dotenv 与浏览器工具尚未安装；仅旧 `.env` 分支才需要 dotenv，现行外盘注入配置不需要它。

`test` 只运行已确认不读取旧配置/数据的存储、mock、migration 和基础 Web 测试。旧全量测试中仍有直接加载仓库配置的入口，本轮没有运行；UI 未改变，未声称浏览器 E2E 或真实微信 API 验收。基本服务验证使用真实 loopback HTTP 与外盘隔离数据库的重启持久性。

本轮删除的是旧 untracked reports、已废弃平台/测试/外部任务 outbox 包、Python bytecode、pytest/Finder cache，合计约 9.78 MB；按所有者 release-first 授权不保留副本。Git 历史、源代码、文章、旧数据库与登录状态均未清理。之后不要用旧的内盘 `.venv` 安装步骤；历史 CLI 配置入口仅供单独批准的旧数据维护。
