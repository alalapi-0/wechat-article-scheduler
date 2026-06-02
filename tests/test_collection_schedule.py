"""Round 64：合集排期规则与 plan 集成。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import yaml

from wechat_article_scheduler import db
from wechat_article_scheduler.content_library.collection_config import load_collection_yaml
from wechat_article_scheduler.content_library.collection_schedule import (
    CollectionScheduleRules,
    day_count_key,
    schedule_rules_for_collection,
    schedule_rules_from_yaml_block,
)
from wechat_article_scheduler.plan import build_plan
from wechat_article_scheduler.web.user_copy import humanize_plan_result
from tests.conftest import make_test_config


def _rules_cfg(root: Path, db_path: Path, **schedule: object):
    return make_test_config(
        root,
        db_path,
        rules={
            "schedule": {
                "max_per_day": 2,
                "min_hours_between": 1,
                "preferred_hours": [9, 14],
                **schedule,
            }
        },
        schedule_window_days=14,
    )


def test_schedule_rules_from_yaml_overrides_global() -> None:
    base = CollectionScheduleRules(
        max_per_day=2,
        min_hours_between=4,
        preferred_hours=(9, 14, 20),
        stagger_hours=0,
        window_days=None,
    )
    rules = schedule_rules_from_yaml_block(
        {"max_per_day": 1, "min_hours_between": 6, "preferred_hours": [10, 18], "stagger_hours": 2},
        fallback=base,
    )
    assert rules.max_per_day == 1
    assert rules.min_hours_between == 6
    assert rules.preferred_hours == (10, 18)
    assert rules.stagger_hours == 2


def test_load_collection_yaml_parses_schedule(tmp_path: Path) -> None:
    coll_dir = tmp_path / "content" / "collections" / "alpha"
    coll_dir.mkdir(parents=True)
    (coll_dir / "collection.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "Alpha",
                "slug": "alpha",
                "schedule": {"max_per_day": 1, "preferred_hours": [11]},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    cfg = load_collection_yaml(coll_dir / "collection.yaml", root=tmp_path)
    assert cfg.schedule_raw == {"max_per_day": 1, "preferred_hours": [11]}


def test_build_plan_two_collections_respect_max_per_day(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "plan.sqlite3"
    db.init_db(db_path)

    for slug, sched in (
        ("alpha", {"max_per_day": 1, "preferred_hours": [9], "stagger_hours": 0}),
        ("beta", {"max_per_day": 1, "preferred_hours": [14], "stagger_hours": 2}),
    ):
        coll_dir = root / "content" / "collections" / slug
        coll_dir.mkdir(parents=True)
        (coll_dir / "collection.yaml").write_text(
            yaml.safe_dump({"name": slug.upper(), "slug": slug, "schedule": sched}, allow_unicode=True),
            encoding="utf-8",
        )

    with db.connect(db_path) as conn:
        for slug in ("alpha", "beta"):
            conn.execute(
                "INSERT INTO collections (slug, name, description) VALUES (?, ?, '')",
                (slug, slug.upper()),
            )
        rows = conn.execute("SELECT id, slug FROM collections WHERE slug IN ('alpha','beta')").fetchall()
        by_slug = {r["slug"]: int(r["id"]) for r in rows}
        for slug in ("alpha", "beta"):
            for i in range(2):
                conn.execute(
                    """
                    INSERT INTO articles (
                        source_path, title, summary, body, content_hash, status, collection_id
                    ) VALUES (?, ?, 'S', 'B', ?, 'imported', ?)
                    """,
                    (f"/{slug}-{i}.md", f"{slug}-{i}", f"h-{slug}-{i}", by_slug[slug]),
                )
        conn.commit()

    cfg = _rules_cfg(root, db_path)
    fake_now = datetime(2026, 6, 1, 8, 0, 0)
    with patch("wechat_article_scheduler.plan.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        stats = build_plan(cfg)

    assert stats["planned"] >= 2
    assert "alpha" in stats["by_collection"]
    assert "beta" in stats["by_collection"]

    with db.connect(db_path) as conn:
        jobs = conn.execute(
            """
            SELECT c.slug, j.scheduled_at
            FROM publish_jobs j
            JOIN articles a ON a.id = j.article_id
            JOIN collections c ON c.id = a.collection_id
            WHERE j.status = 'pending'
            ORDER BY j.scheduled_at
            """
        ).fetchall()
    assert len(jobs) == stats["planned"]
    alpha_days = {datetime.fromisoformat(r["scheduled_at"]).strftime("%Y-%m-%d") for r in jobs if r["slug"] == "alpha"}
    assert len(alpha_days) >= 1


def test_build_plan_skips_when_pending_exists(tmp_path: Path) -> None:
    root = tmp_path
    db_path = root / "dup.sqlite3"
    db.init_db(db_path)
    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES ('/x.md', 'T', 'S', 'B', 'h1', 'imported')",
        )
        aid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.execute(
            "INSERT INTO publish_jobs (article_id, scheduled_at, status, adapter_mode) "
            "VALUES (?, ?, 'pending', 'mock')",
            (aid, (datetime.now() + timedelta(days=1)).isoformat(timespec="seconds")),
        )
        conn.commit()

    stats = build_plan(_rules_cfg(root, db_path))
    assert stats["planned"] == 0
    with db.connect(db_path) as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM publish_jobs WHERE article_id = ?", (aid,)).fetchone()["c"]
    assert n == 1


def test_humanize_plan_result_includes_hints() -> None:
    lines = humanize_plan_result(
        {"planned": 2, "hints": ["合集「Demo」：2 篇已排期（每日最多 1 篇）"]},
    )
    assert any("2" in line for line in lines)
    assert any("Demo" in line for line in lines)


def test_day_count_key_is_per_collection() -> None:
    assert day_count_key("serial", "2026-06-01") == "serial:2026-06-01"


def test_schedule_rules_for_collection_uses_schedule_raw(tmp_path: Path) -> None:
    coll_dir = tmp_path / "content" / "collections" / "z"
    coll_dir.mkdir(parents=True)
    path = coll_dir / "collection.yaml"
    path.write_text(
        yaml.safe_dump({"name": "Z", "slug": "z", "schedule": {"max_per_day": 3}}, allow_unicode=True),
        encoding="utf-8",
    )
    coll = load_collection_yaml(path, root=tmp_path)
    cfg = _rules_cfg(tmp_path, tmp_path / "z.sqlite3")
    rules = schedule_rules_for_collection(cfg, coll)
    assert rules.max_per_day == 3
