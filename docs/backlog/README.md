# Backlog

Status: Backlog / Not current development target

本目录保存长期备选设计，不是当前开发主线。

当前 P0 是个人本地微信公众号发布工作台。阶段一完成前，不实现知乎、豆瓣、小红书、微信视频号、Bilibili、抖音、快手、网易云音乐等平台，也不实现完整多平台 adapter、视频/音频发布、跨项目 publish_manifest 或大型统一 outbox。

## 已归档内容

- `roadmap_40_rounds.md`：参考架构吸收后的旧 40 轮长期蓝图。
- `data_model_design.md`：长期多平台数据模型。
- `adapter_design.md`：长期 adapter registry 设计。
- `platform_capability_matrix.md`：长期平台能力矩阵。
- `content_package_design.md`：长期内容包设计。
- `multi_project_manifest_design.md`：长期多项目 manifest 设计。
- `review_and_proof_design.md`：长期人工确认和 proof 设计。
- `reference_absorption/`：TryPost、Mixpost、BrightBean、browser_mcp 等参考方法记录。

## 使用规则

- 这些文档可以作为后期治理轮输入。
- 不得把这些文档里的平台或 adapter 当成当前已支持能力。
- 若要恢复某项设计，必须先新建治理轮，明确它如何服务微信公众号闭环或后续阶段。
- 不得为了 backlog 设计破坏当前微信公众号 CLI、Web、SQLite 或真实草稿链路。
