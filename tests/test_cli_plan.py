"""CLI plan 命令回归（UnboundLocalError build_plan 阴影）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cli_plan_does_not_raise_unbound_local_error(tmp_path: Path) -> None:
    db_path = tmp_path / "plan.sqlite3"
    env = {
        **dict(__import__("os").environ),
        "PYTHONPATH": str(ROOT / "src"),
        "WECHAT_MODE": "mock",
        "DATABASE_PATH": str(db_path),
    }
    init_proc = subprocess.run(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "init-db"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert init_proc.returncode == 0
    proc = subprocess.run(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "plan"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert "UnboundLocalError" not in (proc.stderr or "")
    assert proc.returncode == 0
    assert "计划完成" in proc.stdout
