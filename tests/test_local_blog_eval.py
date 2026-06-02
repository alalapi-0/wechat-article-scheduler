"""local_blog 评估 dry-run。"""

from wechat_article_scheduler.adapters.local_blog.eval_workflow import build_local_blog_dry_run_plan
from wechat_article_scheduler.adapters.local_blog.plans import list_destinations


def test_static_site_dry_run_recommended():
    plan = build_local_blog_dry_run_plan(destination="static_site")
    assert plan["mode"] == "dry_run"
    assert plan["adapter_type"] == "local_blog"
    assert plan["assessment"]["recommendation"] == "recommended"


def test_wordpress_conditional():
    plan = build_local_blog_dry_run_plan(destination="wordpress")
    assert plan["wordpress_env_hints"]
    assert plan["assessment"]["recommendation"] == "conditional"


def test_list_destinations_three():
    dests = list_destinations()
    assert len(dests) == 3
    ids = {d["id"] for d in dests}
    assert "static_site" in ids
