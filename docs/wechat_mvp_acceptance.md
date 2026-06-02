# 微信公众号发布闭环验收（Round 21）

Status: Phase 1 MVP checklist

## 闭环路径

1. **收录** — 上传/扫描 `articles/inbox`
2. **排期** — plan / 工作台安排时间 + 任务级 `publish_action`
3. **预览** — 作品详情正文预览、封面
4. **草稿** — mock/real 创建与 `update-draft`
5. **执行** — scheduler / run-once；mock 默认不联网
6. **半自动** — browser_assist 干跑 + `waiting_confirmation` + proof
7. **可选发布** — `WECHAT_MODE=real` + `WECHAT_ENABLE_PUBLISH` + 任务「正式发布」

## 回归命令

```bash
WECHAT_MODE=mock .venv/bin/python -m pytest \
  tests/test_wechat_chain_stability.py \
  tests/test_optional_real_publish.py \
  tests/test_publish_proof.py \
  tests/test_wechat_field_matrix.py \
  tests/test_browser_assist_workflow.py -q
python scripts/agent_gate.py gate
```

## 通过标准

- 默认 mock 不联网
- 全局/任务级 draft-only 可区分且 UI 可见
- proof 无则 semi-auto 不标 published
- 其他平台能力仍在 backlog，不阻塞本闭环
