"""草稿创建预检与执行门禁。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from tests.conftest import make_test_config
from wechat_article_scheduler import db
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.article_preflight import build_article_preflight_summary
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from tests.test_web_upload import PNG


def _seed_due_article(config, *, cover_path: str = "") -> None:
    with db.connect(config.database_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path) "
            "VALUES ('inbox/x.md', '预检文章', '摘要', '正文', 'preflight-hash', 'imported', ?)",
            (cover_path,),
        )
        article_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        scheduled_at = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', ?)",
            (article_id, scheduled_at, config.wechat_mode),
        )
        conn.commit()


def test_real_mode_blocks_due_draft_without_valid_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "preflight.sqlite3"
    db.init_db(db_path)
    config = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        wechat_default_thumb_path=str(tmp_path / "missing-default.png"),
    )
    _seed_due_article(config)

    with db.connect(db_path) as conn:
        result = build_publish_preflight(config, conn)
    cover = next(check for check in result["checks"] if check["id"] == "cover")
    assert cover["ok"] is False
    assert cover["required"] is True
    assert result["run_once_gate"]["blocked"] is True
    assert result["ready"] is False

    response = TestClient(create_app(config)).post("/api/run-once")
    assert response.status_code == 200
    assert response.json()["blocked_by_preflight"] is True
    assert response.json()["processed"] == 0


def test_real_mode_accepts_existing_default_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "default-cover.sqlite3"
    db.init_db(db_path)
    default_cover = tmp_path / "default.png"
    default_cover.write_bytes(PNG)
    config = make_test_config(
        tmp_path,
        db_path,
        wechat_mode="real",
        wechat_app_id="test-app",
        wechat_app_secret="test-secret",
        wechat_default_thumb_path=str(default_cover),
    )
    _seed_due_article(config)

    with db.connect(db_path) as conn:
        result = build_publish_preflight(config, conn)
    cover = next(check for check in result["checks"] if check["id"] == "cover")
    assert cover["ok"] is True
    assert "默认封面" in cover["detail"]
    assert result["run_once_gate"]["blocked"] is False


def test_real_mode_blocks_invalid_or_unsupported_explicit_cover(tmp_path: Path) -> None:
    for suffix, content in ((".png", None), (".jpg", b""), (".gif", b"gif"), (".webp", b"webp")):
        case_dir = tmp_path / suffix.removeprefix(".")
        case_dir.mkdir()
        db_path = case_dir / "preflight.sqlite3"
        db.init_db(db_path)
        cover = case_dir / f"cover{suffix}"
        if content is not None:
            cover.write_bytes(content)
        default_cover = case_dir / "default.png"
        default_cover.write_bytes(b"valid-default")
        config = make_test_config(
            case_dir,
            db_path,
            wechat_mode="real",
            wechat_default_thumb_path=str(default_cover),
        )
        _seed_due_article(config, cover_path=str(cover))

        with db.connect(db_path) as conn:
            aggregate = build_publish_preflight(config, conn)
        aggregate_cover = next(c for c in aggregate["checks"] if c["id"] == "cover")
        assert aggregate_cover["ok"] is False
        assert aggregate_cover["required"] is True

        article = build_article_preflight_summary(
            {"title": "封面校验", "summary": "", "body": "正文", "cover_path": str(cover)},
            config,
        )
        article_cover = next(c for c in article["checks"] if c["id"] == "cover")
        assert article_cover["ok"] is False
        assert article_cover["required"] is True


def test_mock_mode_warns_but_does_not_block_missing_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "mock-cover.sqlite3"
    db.init_db(db_path)
    config = make_test_config(tmp_path, db_path, wechat_mode="mock")
    _seed_due_article(config)

    with db.connect(db_path) as conn:
        result = build_publish_preflight(config, conn)
    cover = next(check for check in result["checks"] if check["id"] == "cover")
    assert cover["ok"] is False
    assert cover["required"] is False
    assert result["run_once_gate"]["blocked"] is False
    assert result["ready"] is True


def test_article_preflight_requires_body_and_cover_in_real_mode(tmp_path: Path) -> None:
    db_path = tmp_path / "article-preflight.sqlite3"
    db.init_db(db_path)
    config = make_test_config(tmp_path, db_path, wechat_mode="real")
    result = build_article_preflight_summary(
        {"title": "空正文", "summary": "", "body": "   ", "cover_path": ""},
        config,
    )
    assert result["ready"] is False
    required_failures = {
        check["id"] for check in result["checks"] if check["required"] and not check["ok"]
    }
    assert {"body", "cover"} <= required_failures
