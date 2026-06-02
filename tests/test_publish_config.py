"""发布任务级配置与自动发布执行。"""

from __future__ import annotations

from pathlib import Path

import pytest

from wechat_article_scheduler.config import AppConfig, load_config
from wechat_article_scheduler.publish_config import (
    PublishConfig,
    defaults_from_rules,
    parse_publish_config,
    should_submit_publish,
)
from tests.conftest import make_test_config


def test_load_config_defaults_keep_mock_safe_but_real_test_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WECHAT_MODE", raising=False)
    monkeypatch.delenv("WECHAT_ENABLE_PUBLISH", raising=False)
    monkeypatch.delenv("WEB_AUTO_PUBLISH", raising=False)

    cfg = load_config(env_file=tmp_path / "missing.env")

    assert cfg.wechat_mode == "mock"
    assert cfg.wechat_enable_publish is False
    assert cfg.web_auto_publish is False

    monkeypatch.setenv("WECHAT_MODE", "real")
    real_cfg = load_config(env_file=tmp_path / "missing.env")
    assert real_cfg.wechat_mode == "real"
    assert real_cfg.wechat_enable_publish is True
    assert real_cfg.web_auto_publish is True

    monkeypatch.setenv("WECHAT_ENABLE_PUBLISH", "false")
    monkeypatch.setenv("WEB_AUTO_PUBLISH", "false")
    draft_only = load_config(env_file=tmp_path / "missing.env")
    assert draft_only.wechat_enable_publish is False
    assert draft_only.web_auto_publish is False


def test_should_submit_publish_requires_global_switch(tmp_path: Path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "pc.sqlite3", wechat_mode="real", wechat_enable_publish=False)
    assert should_submit_publish(app_config=cfg, job_config=PublishConfig(publish_action="publish")) is False
    assert should_submit_publish(app_config=cfg, job_config=PublishConfig(publish_action="draft")) is False
    cfg.wechat_enable_publish = True
    assert should_submit_publish(app_config=cfg, job_config=PublishConfig(publish_action="publish")) is True


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
        log_redact_secrets=True,
        log_file=None,
        log_max_bytes=1,
        log_backup_count=1,
        log_level="INFO",
        dry_run=False,
        max_job_retries=3,
        wechat_app_id="",
        wechat_app_secret="",
        wechat_default_thumb_path="",
        wechat_enable_publish=False,
        web_auto_run_due=True,
        web_auto_publish=True,
        web_host="127.0.0.1",
        web_port=8080,
        rules={"publish": {"default_action": "publish", "auto_execute": True}},
    )
    defaults = defaults_from_rules(cfg)
    assert defaults.publish_action == "publish"
    assert defaults.auto_execute is True


def test_parse_publish_config_merges_defaults() -> None:
    defaults = PublishConfig(publish_action="draft", auto_execute=False)
    cfg = parse_publish_config({"publish_action": "publish", "auto_execute": True}, defaults=defaults)
    assert cfg.publish_action == "publish"
    assert cfg.auto_execute is True
