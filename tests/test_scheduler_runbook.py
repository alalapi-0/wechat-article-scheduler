"""Round 70 / 收敛 Round 15：scheduler 常驻运行文档与示例。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "scheduler_runbook.md"
EXAMPLES = ROOT / "deploy" / "examples" / "scheduler"
SCRIPTS = (
    ROOT / "scripts" / "run_scheduler_daemon.sh",
    ROOT / "scripts" / "cron_run_once.sh",
)


@pytest.mark.parametrize(
    "path",
    [
        RUNBOOK,
        EXAMPLES / "README.md",
        EXAMPLES / "com.wechat-article-scheduler.plist.example",
        EXAMPLES / "wechat-article-scheduler.service.example",
        EXAMPLES / "cron-run-once.example",
        *SCRIPTS,
    ],
)
def test_scheduler_runbook_artifacts_exist(path: Path) -> None:
    assert path.is_file(), f"missing {path}"


def test_runbook_covers_deployment_modes() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    for keyword in ("launchd", "systemd", "cron", "tmux", "WECHAT_MODE", "scheduler-health"):
        assert keyword in text, keyword


@pytest.mark.parametrize("script", SCRIPTS)
def test_shell_scripts_syntax_ok(script: Path) -> None:
    subprocess.run(
        ["bash", "-n", str(script)],
        check=True,
        cwd=ROOT,
    )


def test_cli_lists_scheduler_daemon() -> None:
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "-h"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert proc.returncode == 0
    assert "scheduler-daemon" in proc.stdout
