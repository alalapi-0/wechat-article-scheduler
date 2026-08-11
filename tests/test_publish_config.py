"""草稿任务级配置。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler.adapters import get_adapter
from wechat_article_scheduler.config import AppConfig, load_config
from wechat_article_scheduler.publish_config import (
    PublishConfig,
    defaults_from_rules,
    parse_publish_config,
)


def test_load_config_defaults_keep_mock_and_real_draft_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WECHAT_MODE", raising=False)
    monkeypatch.delenv("WEB_AUTO_RUN_DUE", raising=False)
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "missing-rules.yaml"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "config.sqlite3"))
    monkeypatch.setenv("ARTICLES_INBOX", str(tmp_path / "articles" / "inbox"))
    monkeypatch.setenv("LOG_FILE", "")

    cfg = load_config(env_file=tmp_path / "missing.env")

    assert cfg.wechat_mode == "mock"
    assert cfg.web_auto_run_due is True

    monkeypatch.setenv("WECHAT_MODE", "real")
    real_cfg = load_config(env_file=tmp_path / "missing.env")
    assert real_cfg.wechat_mode == "real"
    assert real_cfg.web_auto_run_due is True


def test_invalid_wechat_mode_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WECHAT_MODE", "reel")
    monkeypatch.setenv("RULES_PATH", str(tmp_path / "missing-rules.yaml"))
    with pytest.raises(ValueError, match="mock 或 real"):
        load_config(env_file=tmp_path / "missing.env")

    cfg = AppConfig(
        root=tmp_path,
        database_path=tmp_path / "x.sqlite3",
        inbox_dir=tmp_path / "inbox",
        rules_path=tmp_path / "rules.yaml",
        wechat_mode="typo",
        schedule_window_days=7,
        scheduler_poll_seconds=60,
        max_articles_per_day=2,
        log_file=None,
        log_max_bytes=1,
        log_backup_count=1,
        log_level="INFO",
        dry_run=False,
        max_job_retries=3,
        scheduler_claim_timeout_seconds=900,
        scheduler_lock_ttl_seconds=300,
        scheduler_misfire_grace_minutes=60,
        wechat_app_id="",
        wechat_app_secret="",
        wechat_default_thumb_path="",
        web_auto_run_due=False,
        web_host="127.0.0.1",
        web_port=8080,
        rules={},
    )
    with pytest.raises(ValueError, match="mock 或 real"):
        get_adapter(cfg)


def test_defaults_from_rules() -> None:
    cfg = AppConfig(
        root=Path("."),
        database_path=Path("x"),
        inbox_dir=Path("in"),
        rules_path=Path("r"),
        wechat_mode="mock",
        schedule_window_days=7,
        scheduler_poll_seconds=60,
        max_articles_per_day=2,
        log_file=None,
        log_max_bytes=1,
        log_backup_count=1,
        log_level="INFO",
        dry_run=False,
        max_job_retries=3,
        scheduler_claim_timeout_seconds=900,
        scheduler_lock_ttl_seconds=300,
        scheduler_misfire_grace_minutes=60,
        wechat_app_id="",
        wechat_app_secret="",
        wechat_default_thumb_path="",
        web_auto_run_due=True,
        web_host="127.0.0.1",
        web_port=8080,
        rules={"publish": {"auto_execute": True}},
    )
    defaults = defaults_from_rules(cfg)
    assert defaults.auto_execute is True


def test_parse_publish_config_merges_defaults() -> None:
    defaults = PublishConfig(auto_execute=False, author="默认作者")
    cfg = parse_publish_config(
        {"auto_execute": True, "need_open_comment": True},
        defaults=defaults,
    )
    assert cfg.auto_execute is True
    assert cfg.need_open_comment is True
    assert cfg.author == "默认作者"
