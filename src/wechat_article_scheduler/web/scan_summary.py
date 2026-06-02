"""扫描结果摘要（与 chain_summary 联动展示）。"""

from __future__ import annotations

from typing import Any

CHAIN_ACTION_LABELS = {
    "scan": "扫描收件箱",
    "plan": "生成排期",
    "run-once": "执行到点发布",
    "retry-failed": "重试失败任务",
    "idle": "暂无待办",
}


def format_scan_stats(stats: dict[str, Any]) -> dict[str, Any]:
    scanned = int(stats.get("scanned") or 0)
    imported = int(stats.get("imported") or 0)
    errors = int(stats.get("errors") or 0)
    reconciled = int(stats.get("reconciled_reupload") or 0)
    skipped = int(stats.get("skipped_duplicate") or 0)
    parts = [f"检查 {scanned} 个文件"]
    if imported:
        parts.append(f"新收录 {imported} 篇")
    if reconciled:
        parts.append(f"重传识别 {reconciled} 篇")
    if skipped:
        parts.append(f"跳过重复 {skipped} 篇")
    if errors:
        parts.append(f"失败 {errors} 个")
    if not imported and not reconciled and scanned > 0:
        parts.append("无新收录")
    return {
        "scanned": scanned,
        "imported": imported,
        "errors": errors,
        "reconciled_reupload": reconciled,
        "skipped_duplicate": skipped,
        "summary_label": " · ".join(parts),
    }


def chain_hint_after_scan(chain_summary: dict[str, Any]) -> str | None:
    action = str(chain_summary.get("recommended_next_action") or "")
    if not action or action == "idle":
        return None
    label = CHAIN_ACTION_LABELS.get(action, action)
    without_job = int(chain_summary.get("imported_without_pending_job") or 0)
    if action == "plan" and without_job > 0:
        return f"链路建议：{label}（{without_job} 篇待排期）"
    if action == "run-once":
        due = int(chain_summary.get("due_pending_jobs") or 0)
        return f"链路建议：{label}（{due} 个已到点）"
    return f"链路建议下一步：{label}"
