"""Round 101：工作台与链路摘要合并。"""

from wechat_article_scheduler.web.workbench_mvp import build_workbench_hints


def test_empty_db_suggests_scan_via_chain():
    wb = build_workbench_hints(
        article_counts={},
        job_counts={},
        schedule_summary={"due_now_count": 0},
        chain_summary={
            "recommended_next_action": "scan",
            "recommended_cli": "python -m wechat_article_scheduler.cli scan",
        },
    )
    assert wb["primary_action"] == "scan"
    assert wb["recommended_cli"]
    assert "扫描" in wb["headline"] or "尚无" in wb["headline"]


def test_chain_plan_when_imported_unscheduled():
    wb = build_workbench_hints(
        article_counts={"imported": 2},
        job_counts={},
        schedule_summary={"due_now_count": 0},
        chain_summary={"recommended_next_action": "plan"},
    )
    assert wb["primary_action"] == "plan"
    assert "待生成" in wb["headline"] or "待安排" in wb["headline"]
