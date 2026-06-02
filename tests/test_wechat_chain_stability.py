"""收敛路线图 Round 2：scan -> plan -> run-once 主链路 mock 回归。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.scheduler import run_due_jobs

from tests.conftest import make_test_config


def test_scan_plan_run_once_mock_chain(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "data.sqlite3"
    db.init_db(db_path)

    inbox = root / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "chapter.md").write_text(
        "---\ntitle: 链路测试\ndigest: 摘要\n---\n\n正文。",
        encoding="utf-8",
    )
    (root / "articles" / "imported").mkdir(parents=True)
    (root / "articles" / "published").mkdir(parents=True)

    cfg = make_test_config(
        root,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 2,
                "min_hours_between": 0,
                "preferred_hours": [9],
            }
        },
    )

    scan_stats = scan_inbox(cfg)
    assert scan_stats["imported"] == 1

    plan_stats = build_plan(cfg)
    assert plan_stats["planned"] >= 1

    past = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            "UPDATE publish_jobs SET scheduled_at = ? WHERE status = 'pending'",
            (past,),
        )
        conn.commit()

    run_stats = run_due_jobs(cfg)
    assert run_stats["processed"] >= 1

    with db.connect(db_path) as conn:
        job = conn.execute(
            "SELECT status, adapter_mode FROM publish_jobs"
        ).fetchone()
        draft_count = conn.execute(
            "SELECT COUNT(*) AS c FROM wechat_drafts"
        ).fetchone()["c"]
        assert job["status"] == "done"
        assert job["adapter_mode"] == "mock"
        assert draft_count >= 1
