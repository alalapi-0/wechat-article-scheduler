"""Round 60：公众号效果预览快照。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wechat_article_scheduler import db
from wechat_article_scheduler.config import AppConfig
from tests.conftest import make_test_config


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    db_path = tmp_path / "snap.sqlite3"
    db.init_db(db_path)
    return make_test_config(tmp_path, db_path)
from wechat_article_scheduler.preview_snapshot import (
    APPROXIMATION_NOTE,
    build_article_preview_package,
    latest_snapshot_path,
    preview_snapshots_dir,
    save_preview_snapshot,
)


def test_build_article_preview_package_digest_and_hints(app_config) -> None:
    row = {
        "title": "标题",
        "summary": "x" * 130,
        "body": "",
        "cover_path": "",
    }
    pkg = build_article_preview_package(app_config, row, article_id=1)
    assert pkg["approximation_note"] == APPROXIMATION_NOTE
    assert pkg["digest_truncated"] is True
    assert len(pkg["digest_preview"]) <= 120
    assert "正文为空" in pkg["content_hints"]
    assert "正文为空" in pkg["blocking_hints"]
    assert pkg["cover_url"] is None


def test_save_preview_snapshot_writes_json_and_html(app_config) -> None:
    row = {"title": "T", "summary": "摘要", "body": "段落", "cover_path": ""}
    pkg = build_article_preview_package(app_config, row, article_id=42)
    path = save_preview_snapshot(app_config, pkg)
    assert path.suffix == ".json"
    assert path.parent == preview_snapshots_dir(app_config)
    assert path.with_suffix(".html").is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["package"]["title"] == "T"
    latest = latest_snapshot_path(app_config, 42)
    assert latest == path


def test_preview_snapshot_cli(app_config, capsys, monkeypatch: pytest.MonkeyPatch) -> None:
    from wechat_article_scheduler import cli as cli_mod

    monkeypatch.setattr(cli_mod, "load_config", lambda: app_config)
    monkeypatch.setattr(cli_mod, "setup_logging", lambda _cfg: None)

    with db.connect(app_config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("/tmp/snap.md", "CLI 预览", "摘要", "正文", "snap1", "imported"),
        )
        conn.commit()
        article_id = conn.execute("SELECT id FROM articles").fetchone()[0]

    code = cli_mod.main(["preview-snapshot", "--article-id", str(article_id)])
    assert code == 0
    out = capsys.readouterr().out
    assert "预览快照已保存" in out
    assert latest_snapshot_path(app_config, article_id) is not None


def test_preview_snapshot_cli_missing_article(app_config, monkeypatch: pytest.MonkeyPatch) -> None:
    from wechat_article_scheduler import cli as cli_mod

    monkeypatch.setattr(cli_mod, "load_config", lambda: app_config)
    monkeypatch.setattr(cli_mod, "setup_logging", lambda _cfg: None)
    assert cli_mod.main(["preview-snapshot", "--article-id", "99999"]) == 1
