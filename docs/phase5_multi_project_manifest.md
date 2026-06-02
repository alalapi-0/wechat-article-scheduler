# Phase5 多项目 publish_manifest（Round 39 / agent round_103）

Status: 评估与干跑；**不**写入 SQLite，**不**替代 `scan` / `plan` 微信主线。

## 能力

| 组件 | 说明 |
|------|------|
| `config/projects.example.yaml` | 多项目注册表示例；可复制为 `projects.yaml` |
| `core/projects_registry.py` | 加载与校验 projects 列表 |
| `core/multi_project_dry_run.py` | 按项目批量 `manifest_dry_run` |
| CLI | `projects-dry-run` |
| API | `GET /api/projects/registry`、`GET /api/projects/dry-run` |
| `/debug` | Phase5 多项目 registry 与干跑 JSON |

## 与 round_086/087 关系

- round_086：`validate_manifest` / 单文件校验
- round_087：单 manifest → content_package 干跑
- round_103：多项目 `projects.yaml` 编排上述能力，仍不写库

## 微信主线

文章仍经 `articles/inbox` + `scan` + `plan` + `run-once`。manifest 路径供后续跨项目导入预研，默认仅 dry-run。
