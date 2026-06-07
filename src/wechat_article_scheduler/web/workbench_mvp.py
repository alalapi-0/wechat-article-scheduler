"""Web 控制台 MVP 下一步提示（收敛路线图 Round 10）。"""

from __future__ import annotations

from typing import Any


def build_workbench_hints(
    *,
    article_counts: dict[str, int],
    job_counts: dict[str, int],
    schedule_summary: dict[str, Any] | None,
    chain_summary: dict[str, Any] | None = None,
    publish_preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """根据当前库内状态生成普通用户可读的「下一步」摘要。"""
    imported = int(article_counts.get("imported") or 0)
    pending = int(job_counts.get("pending") or 0)
    failed = int(job_counts.get("failed") or 0)
    total_articles = sum(int(v or 0) for v in article_counts.values())
    sched = schedule_summary or {}
    due_now = int(sched.get("due_now_count") or 0)
    next_summary = str(sched.get("next_summary") or "").strip()
    chain = chain_summary or {}
    chain_action = str(chain.get("recommended_next_action") or "")
    chain_cli = chain.get("recommended_cli")
    without_pending_job = int(chain.get("imported_without_pending_job") or 0)

    hints: list[str] = []
    primary = "idle"
    headline = "欢迎使用本地草稿排期工作台"

    if chain_action == "scan" and total_articles == 0:
        primary = "scan"
        headline = "尚无作品，先扫描或上传"
        hints.append("可将 Markdown 放入 articles/inbox 后点「扫描本地收件箱」")
    elif chain_action == "plan" and without_pending_job > 0:
        primary = "plan"
        headline = f"有 {without_pending_job} 篇已导入，待生成草稿创建计划"
        hints.append("点「自动推荐时间」为作品安排草稿创建时间")
    elif due_now > 0:
        primary = "run"
        headline = f"有 {due_now} 篇已到草稿创建时间"
        hints.append("建议点「执行到点草稿创建」完成演练或创建草稿")
    elif imported > 0 and pending == 0 and without_pending_job > 0:
        primary = "plan"
        headline = f"有 {without_pending_job} 篇作品待安排草稿创建时间"
        hints.append("可点「自动推荐时间」或「自定义安排…」")
        hints.append("也可先把 articles/inbox 里的文件用「扫描本地收件箱」导入")
    elif imported > 0 and pending == 0 and without_pending_job == 0:
        primary = "idle"
        headline = "当前作品草稿流程已走完"
        hints.append("可上传新作品，或在作品详情更新草稿、导出 Agent 任务包")
        hints.append("后台正式发布或定时发布需在公众号后台人工确认")
    elif pending > 0:
        primary = "wait"
        headline = next_summary or f"共有 {pending} 个待创建草稿任务"
        hints.append("到时间后点「执行到点草稿创建」")
    else:
        primary = "upload"
        headline = "作品库还是空的"
        hints.append("拖拽上传作品与封面，或点「扫描本地收件箱」导入本地文件夹")

    preflight = publish_preflight or {}
    preflight_ready = bool(preflight.get("ready", True))
    blocking_checks = [
        c
        for c in (preflight.get("checks") or [])
        if not c.get("ok") and c.get("required")
    ]
    warn_checks = [
        c
        for c in (preflight.get("checks") or [])
        if not c.get("ok") and not c.get("required")
    ]
    if blocking_checks and (pending > 0 or due_now > 0):
        primary = "preflight"
        headline = "草稿创建前检查未通过，请先处理"
        for check in blocking_checks[:2]:
            hints.insert(0, check.get("detail") or check.get("label", "检查项"))
    elif warn_checks and pending > 0 and primary not in ("scan", "upload"):
        for check in warn_checks[:1]:
            hints.append(f"预检提示：{check.get('detail') or check.get('label')}")

    if failed > 0:
        hints.append(f"草稿队列中有 {failed} 个失败任务，请查看原因并重新安排")
    if chain_action == "retry-failed" and failed > 0:
        primary = "retry"
        hints.append("可在草稿队列页重试失败任务，或 CLI：retry-failed")

    if chain_cli and primary in ("scan", "plan", "run", "retry", "idle"):
        hints.append(f"命令行等价：{chain_cli}")

    return {
        "primary_action": primary,
        "headline": headline,
        "hints": hints[:5],
        "chain_recommended_action": chain_action or None,
        "recommended_cli": chain_cli,
        "preflight_ready": preflight_ready,
        "preflight_blocking_count": len(blocking_checks),
    }
