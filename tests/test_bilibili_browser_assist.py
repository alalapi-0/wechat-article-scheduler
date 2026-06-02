"""Round 93：Bilibili browser_assist 评估。"""

from wechat_article_scheduler.adapters.browser_assist.bilibili_workflow import (
    build_bilibili_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.plans import (
    SUPPORTED_BROWSER_ASSIST,
    build_dry_run_plan,
)


def test_bilibili_dry_run_assessment():
    plan = build_bilibili_dry_run_plan()
    assert plan["platform"] == "bilibili"
    assert plan["assessment"]["recommendation"] == "manual_export_first"


def test_plans_entry_bilibili():
    assert "bilibili" in SUPPORTED_BROWSER_ASSIST
    plan = build_dry_run_plan(platform="bilibili")
    assert plan["mode"] == "dry_run"
