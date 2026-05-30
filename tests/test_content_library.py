"""Round 2：内容库集合、标签与审核状态。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.content_library import (
    list_content_items,
    register_imported_article,
    set_review_status,
)
from wechat_article_scheduler.scanner import scan_inbox
from tests.conftest import make_test_config


@pytest.fixture
def lib_config(tmp_path: Path):
    db_path = tmp_path / "lib.sqlite3"
    db.init_db(db_path)
    inbox = tmp_path / "articles" / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "sample.md").write_text("# 标题\n\n正文内容。", encoding="utf-8")
    cfg = make_test_config(tmp_path, db_path)
    return cfg


def test_scan_registers_default_collection_and_draft_status(lib_config) -> None:
    stats = scan_inbox(lib_config)
    assert stats["imported"] == 1
    with db.connect(lib_config.database_path) as conn:
        items = list_content_items(conn, limit=5)
    assert len(items) == 1
    assert items[0].review_status == "draft"
    assert items[0].collection_slug == "default"
    assert items[0].import_batch is not None


def test_set_review_status_updates_article(lib_config) -> None:
    with db.connect(lib_config.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('a.md', 'T', 'S', 'body', 'hash-lib-1', 'imported')
            """
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        register_imported_article(conn, article_id=aid, tag_names=["专栏", "测试"])
        conn.commit()
        set_review_status(conn, aid, "pending_review")
        items = list_content_items(conn, limit=1)
    assert items[0].review_status == "pending_review"
    assert "专栏" in items[0].tags
