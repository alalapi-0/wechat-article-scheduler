"""最小仓库契约检查入口。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repository_contract_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_repo_contract.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
