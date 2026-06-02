"""Round 97：微信视频号 browser_assist。"""

from wechat_article_scheduler.adapters.browser_assist.plans import (
    SUPPORTED_BROWSER_ASSIST,
    build_dry_run_plan,
)
from wechat_article_scheduler.adapters.browser_assist.wechat_channels_workflow import (
    build_wechat_channels_dry_run_plan,
)


def test_channels_dry_run_separate_from_mp():
    plan = build_wechat_channels_dry_run_plan()
    assert plan["platform"] == "wechat_channels"
    assert "微信公众号" in plan["terminal_policy"] or "公众号" in plan["terminal_policy"]


def test_plans_channels_alias():
    assert "wechat_channels" in SUPPORTED_BROWSER_ASSIST
    plan = build_dry_run_plan(platform="channels")
    assert plan["assessment"]["recommendation"] == "manual_export_first"
