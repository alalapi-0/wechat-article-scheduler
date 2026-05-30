from datetime import datetime, timedelta
from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.scheduler import run_due_jobs
from tests.conftest import make_test_config


def test_run_once_truncates_long_digest_and_records_warning(tmp_path: Path) -> None:
    root = tmp_path
    src = root / "articles" / "imported" / "long.md"
    src.parent.mkdir(parents=True)
    src.write_text("body", encoding="utf-8")
    db_path = root / "data.sqlite3"
    db.init_db(db_path)
    past = (datetime.now() - timedelta(minutes=5)).isoformat(timespec="seconds")
    long_summary = "摘" * 180

    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, 'T', ?, 'B', 'h3', 'imported')",
            (str(src), long_summary),
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, past),
        )
        conn.commit()

    cfg = make_test_config(root, db_path)
    stats = run_due_jobs(cfg)
    assert stats["processed"] == 1

    with db.connect(db_path) as conn:
        evt = conn.execute(
            "SELECT event_type FROM events WHERE event_type = 'digest_truncated_warning' LIMIT 1"
        ).fetchone()
        assert evt is not None
