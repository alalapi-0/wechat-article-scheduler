"""Round 96：微信视频号发布包。"""

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


def test_wechat_channels_pack_files(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "wc.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/v.md', '视频号标题', '描述', '正文', 'wc', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = export_article_to_outbox(cfg, conn, aid, platform="wechat_channels")
    assert result["ok"]
    out = Path(result["outbox_path"])
    assert (out / "channels_title.txt").read_text(encoding="utf-8").strip() == "视频号标题"
    assert (out / "channels_publish.md").is_file()
    assert "公众号" in (out / "channels_article_link_note.txt").read_text(encoding="utf-8")
