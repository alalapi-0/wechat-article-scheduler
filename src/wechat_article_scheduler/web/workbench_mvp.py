"""Web 控制台 MVP 下一步提示（收敛路线图 Round 10）。"""

from __future__ import annotations

from typing import Any


def build_workbench_hints(
    *,
    article_counts: dict[str, int],
    job_counts: dict[str, int],
    schedule_summary: dict[str, Any] | None,
    chain_summary: dict[str, Any] | None = None,
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

    hints: list[str] = []
    primary = "idle"
    headline = "欢迎使用本地发布工作台"

    if chain_action == "scan" and total_articles == 0:
        primary = "scan"
        headline = "尚无作品，先扫描或上传"
        hints.append("可将 Markdown 放入 articles/inbox 后点「扫描本地收件箱」")
    elif chain_action == "plan" and imported > 0 and pending == 0:
        primary = "plan"
        headline = f"有 {imported} 篇已导入，待生成发布计划"
        hints.append("点「自动推荐时间」为作品安排发布时间")
    elif due_now > 0:
        primary = "run"
        headline = f"有 {due_now} 篇已到发布时间"
        hints.append("建议点「执行到点发布」完成演练或创建草稿")
    elif imported > 0 and pending == 0:
        primary = "plan"
        headline = f"有 {imported} 篇作品待安排发布时间"
        hints.append("可点「自动推荐时间」或「自定义安排…」")
        hints.append("也可先把 articles/inbox 里的文件用「扫描本地收件箱」导入")
    elif pending > 0:
        primary = "wait"
        headline = next_summary or f"共有 {pending} 个待发布任务"
        hints.append("到时间后点「执行到点发布」")
    else:
        primary = "upload"
        headline = "作品库还是空的"
        hints.append("拖拽上传作品与封面，或点「扫描本地收件箱」导入本地文件夹")

    if failed > 0:
        hints.append(f"发布队列中有 {failed} 个失败任务，请查看原因并重新安排")
    if chain_action == "retry-failed" and failed > 0:
        primary = "retry"
        hints.append("可在发布队列页重试失败任务，或 CLI：retry-failed")

    if chain_cli and primary in ("scan", "plan", "run", "retry", "idle"):
        hints.append(f"命令行等价：{chain_cli}")

    return {
        "primary_action": primary,
        "headline": headline,
        "hints": hints[:4],
        "chain_recommended_action": chain_action or None,
        "recommended_cli": chain_cli,
    }
