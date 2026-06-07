# UX 循环测试汇总

| 轮次 | 日期 | P0 | P1 | 是否修复 | 是否 push | 最高剩余等级 |
|---|---|---|---|---|---|---|
| UX-LOOP-001 | 2026-06-07 | 0 | 4（已修） | 是 | 已 push | P2 |
| UX-LOOP-002 | 2026-06-07 | 0 | 1（已修） | 是 | 已 push | P2 |
| UX-LOOP-003 | 2026-06-07 | 0 | 0 | 是（P2/P4） | 已 push | — |
| UX-LOOP-004 | 2026-06-07 | 0 | 0 | 否 | — | **停止** |

## 已修复 P1（UX-LOOP-001）

- P1-001：`web_auto_publish` 与 `publish_enabled` 语义澄清（effective/ignored）
- P1-002：上传/扫描空文件人话反馈（skipped_empty）
- P1-005：详情页 done 任务下一步矛盾
- P1-006：draft-only 文案（安排发布→排期/草稿）

## LOOP-003 已修复 P2/P4

- P2-001：首页 fast bootstrap + shimmer
- P2-003：flatpickr CDN 回退提示
- P2-004：127.0.0.1 安全说明
- P4-001：多平台导出仅高级模式可见
