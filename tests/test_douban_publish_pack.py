"""Round 80：豆瓣发布包模板。"""

from __future__ import annotations

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


def test_douban_pack_files(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "d.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/d.md', '豆瓣标题', '简介', '正文', 'db', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = export_article_to_outbox(cfg, conn, aid, platform="douban")
    assert result["ok"]
    out = Path(result["outbox_path"])
    assert (out / "douban_title.txt").is_file()
    assert (out / "douban_publish.md").is_file()
    assert (out / "douban_tags_hint.md").is_file()
