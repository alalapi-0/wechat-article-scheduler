"""微信闭环链路摘要。"""

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.scanner import scan_inbox
from wechat_article_scheduler.wechat_chain_summary import build_wechat_chain_summary

from tests.conftest import make_test_config


def test_chain_summary_recommends_scan_when_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "d.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    with db.connect(db_path) as conn:
        summary = build_wechat_chain_summary(cfg, conn)
    assert summary["recommended_next_action"] == "scan"
    assert "scan" in (summary["recommended_cli"] or "")


def test_chain_summary_recommends_plan_after_import(tmp_path: Path) -> None:
    inbox = tmp_path / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "a.md").write_text("---\ntitle: T\n---\n\nbody", encoding="utf-8")
    (tmp_path / "articles" / "imported").mkdir(parents=True)
    (tmp_path / "articles" / "published").mkdir(parents=True)
    db_path = tmp_path / "d.sqlite3"
    db.init_db(db_path)
    cfg = make_test_config(tmp_path, db_path)
    scan_inbox(cfg)
    with db.connect(db_path) as conn:
        summary = build_wechat_chain_summary(cfg, conn)
    assert summary["recommended_next_action"] == "plan"
