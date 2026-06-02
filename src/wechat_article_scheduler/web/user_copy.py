"""普通用户文案映射（Round 20+ 单一来源）。

展示层翻译：不改数据库字段名或 API 内部枚举，仅用于 Web 普通视图。
"""

from __future__ import annotations

from wechat_article_scheduler.publish_config import PublishConfig, human_publish_action_label

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
    "waiting_confirmation": "待人工确认",
}

EVENT_TYPE: dict[str, str] = {
    "scan_imported": "收录文章",
    "scan_reupload_reconciled": "重新上传已绑定",
    "plan_created": "创建发布计划",
    "job_started": "开始发布",
    "job_done": "发布完成",
    "waiting_confirmation": "进入待人工确认",
    "proof_submitted": "已提交发布证明",
    "draft_created": "微信草稿已创建",
    "job_failed": "发布失败",
    "digest_warning": "摘要提醒",
    "dry_run": "演练执行",
}

MODE_LABELS: dict[str, str] = {
    "mock": "演练（不会真的发到公众号）",
    "real": "真实 API 测试（按任务设置创建草稿或正式发布）",
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
    "upload": "上传作品与封面",
    "scan": "扫描收件箱",
    "plan": "自动推荐时间",
    "run-once": "执行到点发布",
    "status": "刷新状态",
}

STEP_LABELS: tuple[str, str, str] = (
    "1 收录作品：拖拽上传，或扫描本地收件箱（articles/inbox）",
    "2 安排时间：自动推荐或自定义设定发布时间",
    "3 执行到点：到时间后执行发布或演练",
)

EMPTY_MESSAGES: dict[str, str] = {
    "jobs": "还没有待发布作品。先在上方上传作品，再点「安排发布时间」。",
    "events": "还没有操作记录。完成上传、排期或执行后，这里会显示你刚才做了什么。",
    "articles": "作品库还是空的。把文章（md/txt/html）和封面图拖到上传区，或点「选择文件」即可收录。",
    "overview": "欢迎使用本地发布工作台。建议按三步开始：先上传作品，再安排时间，最后到点执行。",
}


def label_article_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return ARTICLE_STATUS.get(key, status or "未知")


def article_workflow_hint(
    *,
    status: str | None,
    latest_job_status: str | None,
    has_wechat_draft: bool,
) -> str:
    """作品库卡片上的下一步状态提示（普通视图）。"""
    st = (status or "").strip().lower()
    job = (latest_job_status or "").strip().lower()
    if st == "published":
        return "已发布"
    if st == "imported":
        if job == "pending":
            return "待发布（已排期）"
        if job == "running":
            return "发布中"
        if job == "failed":
            return "发布失败，可重新安排"
        if job == "waiting_confirmation":
            return "待人工确认 · 需回填发布证明"
        if has_wechat_draft:
            return "已收录 · 微信草稿已创建"
        return "待安排发布"
    return label_article_status(status)


def label_job_status(status: str | None) -> str:
    key = (status or "").strip().lower()
    return JOB_STATUS.get(key, status or "未知")


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
    reconciled = payload.get("reconciled_articles") or []
    lines = [f"已检查 {scanned} 个文件"]
    if imported:
        lines.append(f"新收录 {imported} 篇文章")
    elif reconciled:
        for item in reconciled:
            title = str(item.get("title") or "该作品")
            if item.get("status_reset"):
                lines.append(f"《{title}》已在作品库中，已识别为重新上传并重置为待发布")
            else:
                lines.append(f"《{title}》已在作品库中，可继续安排发布")
    else:
        lines.append("没有发现新的文章")
    if errors:
        lines.append(f"有 {errors} 个文件处理失败，请检查收件箱格式")
    return lines


def humanize_plan_result(payload: dict[str, Any]) -> list[str]:
    planned = int(payload.get("planned") or 0)
    hints = payload.get("hints") or []
    if isinstance(hints, list) and hints:
        lines = [str(h) for h in hints if h]
        if planned:
            lines.insert(0, f"已按合集规则为 {planned} 篇文章安排发布时间")
        return lines
    if planned:
        return [f"已按推荐时段自动为 {planned} 篇文章安排发布时间"]
    return ["没有需要新安排的文章（可能已全部排期）"]


def humanize_schedule_single_result(payload: dict[str, Any]) -> list[str]:
    title = (payload.get("title") or "该作品").strip()
    when = payload.get("scheduled_at_label") or payload.get("scheduled_at") or ""
    verb = "已安排" if payload.get("created", True) else "已更新"
    lines = [f"《{title}》{verb}发布时间为 {when}"]
    pub = payload.get("publish_config") or {}
    if pub:
        cfg = PublishConfig(**{k: pub[k] for k in pub if k in PublishConfig.__dataclass_fields__})
        action = human_publish_action_label(cfg)
        if pub.get("auto_execute"):
            lines.append(f"发布方式：{action}，到点自动执行")
        else:
            lines.append(f"发布方式：{action}，需手动执行到点")
    return lines


def humanize_schedule_batch_result(stats: dict[str, Any]) -> list[str]:
    scheduled = int(stats.get("scheduled") or 0)
    updated = int(stats.get("updated") or 0)
    skipped = int(stats.get("skipped") or 0)
    total = scheduled + updated
    if not total:
        return ["没有作品被安排（请确认已选中「已收录」作品）"]
    lines = [f"已为 {total} 篇作品安排发布时间与配置"]
    pub = stats.get("publish_config") or {}
    if pub:
        cfg = PublishConfig(**{k: pub[k] for k in pub if k in PublishConfig.__dataclass_fields__})
        action = human_publish_action_label(cfg)
        if pub.get("auto_execute"):
            lines.append(f"统一设置：{action}，到点自动执行")
        else:
            lines.append(f"统一设置：{action}，需手动执行到点")
    if skipped:
        lines.append(f"跳过 {skipped} 篇（不存在或不可排期）")
    return lines


def humanize_retry_jobs_result(payload: dict[str, Any]) -> list[str]:
    retried = int(payload.get("retried") or 0)
    if retried:
        return [f"已将 {retried} 个失败任务重新加入待发布队列"]
    return ["没有可重试的失败任务"]


def humanize_run_once_result(payload: dict[str, Any]) -> list[str]:
    processed = int(payload.get("processed") or 0)
    drafted = int(payload.get("drafted") or 0)
    skipped = int(payload.get("skipped_future") or 0)
    failed = int(payload.get("failed") or 0)
    lines: list[str] = []
    if drafted:
        lines.append(f"已创建 {drafted} 个微信草稿")
    if processed:
        if drafted and drafted == processed:
            pass
        else:
            lines.append(f"已处理 {processed} 个到点任务")
    if skipped:
        lines.append(f"有 {skipped} 个任务还没到发布时间")
    if failed:
        lines.append(f"有 {failed} 个任务失败，请查看发布队列")
    skipped_content = int(payload.get("skipped_content") or 0)
    if skipped_content:
        lines.append(
            f"有 {skipped_content} 个任务因内容质量问题未执行（真实正式发布已阻断，请先预览/修复）"
        )
    if not lines:
        lines.append("当前没有需要执行的任务")
    return lines


def export_labels_json() -> dict[str, Any]:
    """供 Web 前端与普通视图测试使用的文案包。"""
    return {
        "article_status": ARTICLE_STATUS,
        "job_status": JOB_STATUS,
        "event_type": EVENT_TYPE,
        "mode": MODE_LABELS,
        "publish_switch": {str(k): v for k, v in PUBLISH_SWITCH.items()},
        "dry_run": {str(k): v for k, v in DRY_RUN_LABELS.items()},
        "actions": ACTION_LABELS,
        "steps": list(STEP_LABELS),
        "empty": EMPTY_MESSAGES,
        "forbidden_ordinary_terms": list(FORBIDDEN_ORDINARY_TERMS),
    }
