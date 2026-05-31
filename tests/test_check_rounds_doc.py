"""Round 12：文档一致性检查脚本测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_check_rounds_doc_passes():
    py = sys.executable
    proc = subprocess.run(
        [py, "scripts/check_rounds_doc.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_round_smoke_hints_file_exists():
    path = ROOT / "governance" / "round_smoke_hints.yaml"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "round_012:" in text
    assert "check_rounds_doc.py" in text
