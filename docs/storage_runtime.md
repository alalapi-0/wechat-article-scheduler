# Linux 存储与运行

当前入口为 `python3 -I -B scripts/storage_runtime.py`，状态声明在 `project.yaml`。本机 CPython 3.12 与专属 `.venv` 位于 `/home/alalapi/Runtimes/wechat-article-scheduler`；缓存和临时根分别为 `/home/alalapi/Caches/wechat-article-scheduler` 与 `/home/alalapi/Temp/wechat-article-scheduler`。新增数据 profile 为 `/home/alalapi/ProjectData/wechat-article-scheduler/linux-local-profile/mock`。旧 ProjectData、仓库 `.env`、rules、文章、数据库和账号状态不加载。

`configs/linux-runtime.json` 登记固定 ext4 UUID `9d258b70-f313-4a5d-9cf6-c715c5edca3d`、`/dev/nvme0n1p3`、挂载点 `/`、目录逐级设备/inode/UID/GID/权限、系统 Python 哈希、虚拟环境身份与依赖版本。守卫以 no-follow 目录描述符核对，不接受路径别名、其他挂载、缺根或工具链漂移；失败先于 profile 遍历、环境执行和应用导入。此清单是本机登记，不可迁到另一主机直接使用旧 inode。

```sh
python3 -I -B scripts/storage_runtime.py check
python3 -I -B scripts/storage_runtime.py cli init-db
python3 -I -B scripts/storage_runtime.py cli serve --port 8080
python3 -I -B scripts/storage_runtime.py cli --help
python3 -I -B scripts/storage_runtime.py test
python3 -I -B scripts/storage_runtime.py contract
python3 -I -B scripts/test_linux_profile.py current
```

运行入口擦除调用者环境，以固定 `-I -B` 解释器执行；不继承凭据、用户 site packages 或外部 PYTHONPATH。权限掩码为 0077。配置固定 mock、dry-run、自动到点执行关闭、任务包导出关闭、空凭据，Web 只允许 loopback。请求 `WECHAT_MODE=real` 在这个入口退出 78；原产品 real adapter 与发布权限边界仍保留，需另行授权和选择配置。此运行 profile 没有导入旧数据，也不代表真实微信、实际发布 proof 或常驻调度已验收。

环境确实缺失时，`rebuild` 校验专属缓存中登记的兼容 wheel 哈希，再以系统 Python 创建 `.venv`、离线安装并执行 `pip check`，更新本机虚拟环境身份登记。已有 `.venv`（含链接）拒绝覆盖；缺 wheel 或校验失败时停止，不下载替代品，不使用历史 Mac 包或其他环境。

`test` 覆盖原存储测试、mock adapter、迁移和基础 Web；包含实际 loopback HTTP 与 SQLite 重启持久性。完整测试入口只复制明确允许的源码、测试、文档、部署样例和合成 fixtures，逐文件校验相同字节；不复制原 `.env`、rules、数据库、articles 或 storage。所有普通 Python 子进程使用这个空配置副本，测试临时目录为私有权限。测试用 Python loopback 连接守卫记录外网尝试，它不是内核沙箱或恶意测试隔离；应用使用固定 mock 配置。测试断言、失败和浏览器条件跳过保留，不能将跳过声称为浏览器验收。

测试报告固定写入专属 Temp 的 `current-pytest.xml`、`current-pytest.txt` 和 `current-source-view.json`，临时源码副本与 pytest fixtures 自动回收；不写 tracked 运行产物。工作站迁移的实际验收、原始分母与远端交付由 Hub inventory 本项目条目记录，业务事实继续由 `project.yaml` 负责。

历史 Mac 存储调查与原数据保留在迁移归档；此前约 9.78 MB 的清理记录不构成本次删除授权。现有 Linux 副本不执行旧 Mac 运行时、不访问 APFS、不清理旧数据或账号状态。
