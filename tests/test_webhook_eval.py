"""Webhook 评估 dry-run。"""

from wechat_article_scheduler.adapters.registry import is_known_adapter
from wechat_article_scheduler.adapters.webhook.eval_workflow import build_webhook_dry_run_plan
from wechat_article_scheduler.adapters.webhook.plans import list_channels


def test_generic_webhook_dry_run():
    plan = build_webhook_dry_run_plan(channel="generic", article_id="42")
    assert plan["mode"] == "dry_run"
    assert plan["terminal_policy"].find("published") >= 0
    assert plan["payload_preview"]["article_id"] == "42"


def test_registry_notification_webhook():
    assert is_known_adapter("notification", "webhook")


def test_list_channels():
    assert len(list_channels()) >= 3
