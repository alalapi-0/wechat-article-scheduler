"""Round 72 / 收敛 Round 17：微信字段能力矩阵。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wechat_article_scheduler.wechat_field_matrix import (
    API_SUPPORT_VALUES,
    IMPLEMENTED_VALUES,
    REQUIRED_KEYS,
    WECHAT_FIELD_MATRIX,
    field_gaps,
    matrix_summary,
)
from wechat_article_scheduler.web import create_app
from tests.conftest import make_test_config

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "wechat_capability_matrix.md"


def test_matrix_rows_complete() -> None:
    assert len(WECHAT_FIELD_MATRIX) >= 12
    ids = {r["field_id"] for r in WECHAT_FIELD_MATRIX}
    assert len(ids) == len(WECHAT_FIELD_MATRIX)
    for row in WECHAT_FIELD_MATRIX:
        assert REQUIRED_KEYS.issubset(row.keys())
        assert row["api_support"] in API_SUPPORT_VALUES
        assert row["implemented"] in IMPLEMENTED_VALUES
        assert row["label"].strip()
        assert row["handling"].strip()


def test_required_fields_present() -> None:
    for fid in (
        "title",
        "digest",
        "body",
        "cover_thumb",
        "local_schedule",
        "wechat_backend_schedule",
        "draft_update",
    ):
        assert fid in {r["field_id"] for r in WECHAT_FIELD_MATRIX}


def test_gaps_include_unverified_schedule() -> None:
    gaps = field_gaps()
    ids = {g["field_id"] for g in gaps}
    assert "wechat_backend_schedule" in ids


def test_matrix_doc_lists_field_ids() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "## 字段级能力矩阵" in text
    for row in WECHAT_FIELD_MATRIX:
        assert row["field_id"] in text


def test_api_field_matrix_endpoint(tmp_path) -> None:
    cfg = make_test_config(tmp_path, tmp_path / "m.sqlite3")
    client = TestClient(create_app(cfg))
    data = client.get("/api/wechat-field-matrix").json()
    assert data["summary"]["total"] == len(WECHAT_FIELD_MATRIX)
    assert len(data["fields"]) == len(WECHAT_FIELD_MATRIX)
    assert "gaps" in data


def test_cli_field_matrix() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "wechat_article_scheduler.cli", "field-matrix"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["summary"]["total"] >= 12
