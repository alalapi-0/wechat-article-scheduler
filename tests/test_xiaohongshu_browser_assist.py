"""Round 95：小红书 browser_assist。"""

from wechat_article_scheduler.adapters.browser_assist.plans import (
    SUPPORTED_BROWSER_ASSIST,
    build_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.xiaohongshu_workflow import (
    build_xiaohongshu_dry_run_plan,
)


def test_xhs_dry_run_deferred():
    plan = build_xiaohongshu_dry_run_plan()
    assert plan["assessment"]["recommendation"] == "deferred"


def test_plans_xhs_alias():
    assert "xiaohongshu" in SUPPORTED_BROWSER_ASSIST
    plan = build_dry_run_plan(platform="xhs")
    assert plan["platform"] == "xiaohongshu"
