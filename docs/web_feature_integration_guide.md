# 后续 Web 功能接入规范（Round 38）

新增功能接入 Web 控制台前，必须先填写以下模板并更新 `docs/info_layer_boundary.md`。

## 1. 功能接入模板

| 字段 | 说明 |
|---|---|
| 功能名 | 如「封面裁剪」「多合集排期」 |
| 普通用户目标 | 一句话说明用户要完成什么 |
| 主操作入口 | 放在首屏 / 详情 / 仅高级 |
| 成功反馈 | 人话摘要 |
| 失败反馈 | 原因 + 影响 + 下一步 |
| 高级字段 | 内部 id、JSON、路径等 |

## 2. 普通 / 详情 / 高级字段清单模板

复制下表到功能设计文档：

| 字段 | 普通 | 详情 | 高级 |
|---|---|---|---|
| （示例）标题 | ✓ | ✓ | — |
| （示例）retry_count | — | — | ✓ |

## 3. 错误解释模板

| 错误场景 | 普通用户看到 | 高级区保留 |
|---|---|---|
| 扫描失败 | 收件箱路径不存在，请检查文件夹 | 原始 exception |
| 排期失败 | 没有可排期文章 | API payload |

## 4. 验收模板

- [ ] 普通首屏无新增裸内部词
- [ ] `tests/test_web_ordinary_copy.py` 通过
- [ ] 有 Playwright 截图或 E2E 更新（如影响布局）
- [ ] `docs/rounds.md` 与 agent_gate 同步

## 5. agent_gate 建议

实现完成后运行：

```bash
python -m pytest tests/test_web_ordinary_copy.py tests/test_ui_e2e.py -q
python scripts/agent_gate.py gate
```
