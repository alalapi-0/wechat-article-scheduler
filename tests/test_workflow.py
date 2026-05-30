from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from wechat_article_scheduler.workflow import reject_article, retry_failed_jobs


def _cfg(root: Path, db_path: Path) -> AppConfig:
    return AppConfig(
        root=root,
        database_path=db_path,
        inbox_dir=root / "articles" / "inbox",
        rules_path=root / "config" / "rules.yaml",
        wechat_mode="mock",
        schedule_window_days=7,
        scheduler_poll_seconds=60,
        max_articles_per_day=2,
        log_redact_secrets=True,
        wechat_app_id="",
        wechat_app_secret="",
        rules={},
    )


def test_reject_and_retry(tmp_path: Path) -> None:
    root = tmp_path
    src = root / "articles" / "imported" / "x.md"
    src.parent.mkdir(parents=True)
    src.write_text("x", encoding="utf-8")
    db_path = root / "d.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, 't', '', 'b', 'h', 'imported')",
            (str(src),),
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, datetime('now'), 'pending', 'mock')",
            (aid,),
        )
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, datetime('now'), 'failed', 'mock')",
            (aid,),
        )
        conn.commit()

    cfg = _cfg(root, db_path)
    assert reject_article(cfg, aid) is True
    n = retry_failed_jobs(cfg)
    assert n >= 1

    with db.connect(db_path) as conn:
        art = conn.execute("SELECT status FROM articles WHERE id = ?", (aid,)).fetchone()
        assert art["status"] == "rejected"
