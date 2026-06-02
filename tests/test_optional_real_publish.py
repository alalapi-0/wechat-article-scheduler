"""Round 75 / 收敛 Round 20：可选正式发布策略。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from wechat_article_scheduler import db
from wechat_article_scheduler.publish_config import PublishConfig
from wechat_article_scheduler.publish_policy import (
    global_publish_policy,
    resolve_effective_submit,
)
from wechat_article_scheduler.web import create_app
from wechat_article_scheduler.web.publish_preflight import build_publish_preflight
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "optional_real_publish.md"


def _seed_pending_publish_job(tmp_path: Path, *, action: str = "publish") -> tuple[Any, int]:
    cfg = make_test_config(tmp_path, tmp_path / "o.sqlite3")
    db.init_db(cfg.database_path)
    import json

    pub_json = json.dumps({"publish_action": action, "auto_execute": False})
    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('inbox/x.md', 'T', 'S', 'body', 'h2', 'imported', 'covers/x.png')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, ?, 'pending', 'mock', ?)
            """,
            (aid, (datetime.now() + timedelta(hours=1)).isoformat(), pub_json),
        )
        conn.commit()
    return cfg, int(aid)


def test_global_policy_mock_default(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "m.sqlite3")
    pol = global_publish_policy(cfg)
    assert pol["badge"] == "mock"
    assert "演练" in pol["headline"]


def test_resolve_real_draft_only_blocks_publish(tmp_path: Path) -> None:
    cfg = make_test_config(
        tmp_path,
        tmp_path / "d.sqlite3",
        wechat_mode="real",
        wechat_enable_publish=False,
    )
    eff = resolve_effective_submit(
        app_config=cfg,
        job_config=PublishConfig(publish_action="publish"),
    )
    assert eff["will_submit"] is False
    assert eff["level"] == "global_draft_only"


def test_task_draft_only_even_when_publish_enabled(tmp_path: Path) -> None:
    cfg = make_test_config(
        tmp_path,
        tmp_path / "p.sqlite3",
        wechat_mode="real",
        wechat_enable_publish=True,
    )
    eff = resolve_effective_submit(
        app_config=cfg,
        job_config=PublishConfig(publish_action="draft"),
    )
    assert eff["will_submit"] is False
    assert eff["level"] == "task_draft_only"


def test_status_api_includes_publish_policy(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "s.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/status").json()
    assert "publish_policy" in data
    assert data["publish_policy"]["headline"]


def test_preflight_task_mix(tmp_path: Path) -> None:
    cfg, _ = _seed_pending_publish_job(tmp_path, action="publish")
    cfg = make_test_config(
        tmp_path,
        tmp_path / "o.sqlite3",
        wechat_mode="real",
        wechat_enable_publish=False,
    )
    db.init_db(cfg.database_path)
    import json

    with db.connect(cfg.database_path) as conn:
        conn.execute(
            """
            INSERT INTO articles (source_path, title, summary, body, content_hash, status, cover_path)
            VALUES ('inbox/a.md', 'A', 'S', 'b', 'h3', 'imported', 'c.png')
            """
        )
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """
            INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode, publish_config_json)
            VALUES (?, datetime('now'), 'pending', 'mock', ?)
            """,
            (aid, json.dumps({"publish_action": "publish"})),
        )
        conn.commit()
        pf = build_publish_preflight(cfg, conn)
    assert pf["pending_task_mix"]["publish_tasks"] >= 1
    assert pf["pending_task_mix"]["blocked_publish_tasks"] >= 1


def test_optional_real_publish_doc() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "WECHAT_ENABLE_PUBLISH" in text
    assert "publish_action" in text
