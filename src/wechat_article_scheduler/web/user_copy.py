"""普通用户文案映射（Round 20+ 单一来源）。

展示层翻译：不改数据库字段名或 API 内部枚举，仅用于 Web 普通视图。
"""

from __future__ import annotations

from typing import Any

# 普通视图禁止直接出现的裸内部词（Round 20 基线检查）
FORBIDDEN_ORDINARY_TERMS: tuple[str, ...] = (
    "publish_jobs",
    "payload_json",
    "skipped_future",
    "wechat_enable_publish",
    "imported",
    "pending",
    "mock",
    "DRY_RUN",
)

ARTICLE_STATUS: dict[str, str] = {
    "imported": "已收录",
    "published": "已发布",
    "draft": "草稿",
    "archived": "已归档",
}

JOB_STATUS: dict[str, str] = {
    "pending": "待发布",
    "running": "发布中",
    "done": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
}

REVIEW_STATUS: dict[str, str] = {
    "draft": "草稿",
    "pending_review": "待审核",
    "approved": "已通过",
    "rejected": "已驳回",
}

EVENT_TYPE: dict[str, str] = {
    "scan_imported": "收录文章",
    "plan_created": "创建发布计划",
    "job_started": "开始发布",
    "job_done": "发布完成",
    "job_failed": "发布失败",
    "digest_warning": "摘要提醒",
    "dry_run": "演练执行",
}

MODE_LABELS: dict[str, str] = {
    "mock": "演练（不会真的发到公众号）",
    "real": "真实连接（需人工确认才会发布）",
}

PUBLISH_SWITCH: dict[bool, str] = {
    False: "不会真的发布",
    True: "已允许真实发布（请谨慎）",
}

DRY_RUN_LABELS: dict[bool, str] = {
    False: "正常执行",
    True: "仅演练不写入",
}

ACTION_LABELS: dict[str, str] = {
    "scan": "扫描收件箱",
    "plan": "安排发布时间",
    "run-once": "执行到点文章",
    "status": "刷新状态",
}

STEP_LABELS: tuple[str, str, str] = (
    "1 找文章：扫描收件箱，把新文章收进来",
    "2 安排时间：为文章设定发布时间",
    "3 执行到点：到时间后执行发布或演练",
)

EMPTY_MESSAGES: dict[str, str] = {
    "jobs": "还没有待发布文章。请先把文章放进收件箱，再点「扫描收件箱」，然后「安排发布时间」。",
    "events": "还没有操作记录。完成扫描、排期或执行后，这里会显示你刚才做了什么。",
    "articles": "还没有收录文章。请把 Markdown 文章放进收件箱文件夹，再点「扫描收件箱」。",
    "overview": "欢迎使用本地工作台。建议按上方三步开始：先把文章放进收件箱，再扫描、排期。",
}


def label_article_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return ARTICLE_STATUS.get(key, status or "未知")


def label_job_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return JOB_STATUS.get(key, status or "未知")


def label_review_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return REVIEW_STATUS.get(key, status or "未知")


def label_event_type(event_type: str | None) -> str:
    key = (event_type or "").strip().lower()
    return EVENT_TYPE.get(key, event_type or "系统事件")


def label_mode(mode: str | None) -> str:
    key = (mode or "").strip().lower()
    return MODE_LABELS.get(key, mode or "未知模式")


def humanize_scan_result(payload: dict[str, Any]) -> list[str]:
    imported = int(payload.get("imported") or 0)
    scanned = int(payload.get("scanned") or 0)
    errors = int(payload.get("errors") or 0)
    lines = [f"已检查 {scanned} 个文件"]
    if imported:
        lines.append(f"新收录 {imported} 篇文章")
    else:
        lines.append("没有发现新的文章")
    if errors:
        lines.append(f"有 {errors} 个文件处理失败，请检查收件箱格式")
    return lines


def humanize_plan_result(payload: dict[str, Any]) -> list[str]:
    planned = int(payload.get("planned") or 0)
    if planned:
        return [f"已为 {planned} 篇文章安排发布时间"]
    return ["没有需要新安排的文章（可能已全部排期）"]


def humanize_run_once_result(payload: dict[str, Any]) -> list[str]:
    processed = int(payload.get("processed") or 0)
    skipped = int(payload.get("skipped_future") or 0)
    skipped_approval = int(payload.get("skipped_not_approved") or 0)
    failed = int(payload.get("failed") or 0)
    lines: list[str] = []
    if processed:
        lines.append(f"已处理 {processed} 个到点任务")
    if skipped:
        lines.append(f"有 {skipped} 个任务还没到发布时间")
    if skipped_approval:
        lines.append(f"有 {skipped_approval} 个任务因未审核通过而跳过")
    if failed:
        lines.append(f"有 {failed} 个任务失败，请查看发布队列")
    if not lines:
        lines.append("当前没有需要执行的任务")
    return lines


def export_labels_json() -> dict[str, Any]:
    """供 Web 前端与普通视图测试使用的文案包。"""
    return {
        "article_status": ARTICLE_STATUS,
        "job_status": JOB_STATUS,
        "review_status": REVIEW_STATUS,
        "event_type": EVENT_TYPE,
        "mode": MODE_LABELS,
        "publish_switch": {str(k): v for k, v in PUBLISH_SWITCH.items()},
        "dry_run": {str(k): v for k, v in DRY_RUN_LABELS.items()},
        "actions": ACTION_LABELS,
        "steps": list(STEP_LABELS),
        "empty": EMPTY_MESSAGES,
        "forbidden_ordinary_terms": list(FORBIDDEN_ORDINARY_TERMS),
    }
