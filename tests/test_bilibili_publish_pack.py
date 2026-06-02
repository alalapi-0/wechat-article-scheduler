"""Round 92：Bilibili 发布包模板。"""

from __future__ import annotations

from pathlib import Path

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


def test_bilibili_pack_files(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "b.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES ('inbox/b.md', 'B站标题', '简介文案', '正文', 'bb', 'imported')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = export_article_to_outbox(cfg, conn, aid, platform="bilibili")
    assert result["ok"]
    out = Path(result["outbox_path"])
    assert (out / "bilibili_title.txt").read_text(encoding="utf-8").strip() == "B站标题"
    assert (out / "bilibili_upload_checklist.md").is_file()
    assert (out / "bilibili_video_placeholder.txt").is_file()
