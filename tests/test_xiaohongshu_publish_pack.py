"""Round 94：小红书发布包。"""

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


def test_xiaohongshu_pack_files(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "x.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/x.md', '小红书标题', '导语', '正文内容', 'xh', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = export_article_to_outbox(cfg, conn, aid, platform="xiaohongshu")
    assert result["ok"]
    out = Path(result["outbox_path"])
    assert (out / "xhs_title.txt").read_text(encoding="utf-8").strip() == "小红书标题"
    assert (out / "xhs_publish_checklist.md").is_file()
    assert (out / "xhs_media_placeholder.txt").is_file()
