"""Round 99：抖音/快手 deferred 评估。"""

from wechat_article_scheduler.adapters.registry import is_known_adapter
from wechat_article_scheduler.content_packages.short_video_deferred import (
    build_short_video_deferred_plan,
    list_short_video_platforms,
)


def test_douyin_deferred_plan():
    plan = build_short_video_deferred_plan(platform="douyin")
    assert plan["assessment"]["recommendation"] == "deferred"


def test_kuaishou_alias_ks():
    plan = build_short_video_deferred_plan(platform="ks")
    assert plan["platform"] == "kuaishou"


def test_registry_douyin_kuaishou():
    assert is_known_adapter("douyin", "manual_export")
    assert is_known_adapter("kuaishou", "manual_export")
    assert len(list_short_video_platforms()) == 2
