"""Round 98：抖音/快手发布包。"""

from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.adapters.manual_export import export_article_to_outbox
from tests.conftest import make_test_config


@pytest.mark.parametrize("platform,prefix", [("douyin", "douyin"), ("kuaishou", "kuaishou")])
def test_short_video_pack_files(tmp_path: Path, platform: str, prefix: str) -> None:
    cfg = make_test_config(tmp_path, tmp_path / f"{platform}.sqlite3")
    db.init_db(cfg.database_path)
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status)
            VALUES (?, '短视频标题', '文案', '正文', ?, 'imported')
            """,
            (f"inbox/{platform}.md", platform),
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        result = export_article_to_outbox(cfg, conn, aid, platform=platform)
    assert result["ok"]
    out = Path(result["outbox_path"])
    assert (out / f"{prefix}_title.txt").is_file()
    assert (out / f"{prefix}_video_placeholder.txt").is_file()
    assert (out / f"{prefix}_publish.md").is_file()
