"""只读暴露 governance/round_state.yaml 中的路线图位置（工作台高级面板）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from wechat_article_scheduler.config import ROOT

ROUND_STATE_PATH = ROOT / "governance" / "round_state.yaml"

DOC_LINKS = (
    {"label": "开发路线图", "path": "docs/rounds.md"},
    {"label": "Backlog", "path": "docs/backlog/README.md"},
)


def load_round_state() -> dict[str, Any]:
    if not ROUND_STATE_PATH.is_file():
        return {}
    raw = yaml.safe_load(ROUND_STATE_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def build_roadmap_status_fields() -> dict[str, Any]:
    """供 /api/status 与 overview.status 使用的只读字段。"""
    data = load_round_state()
    cur = data.get("current_round")
    if not isinstance(cur, dict):
        cur = {}
    lcr_raw = data.get("last_completed_round")
    last_completed_round: dict[str, str] | None = None
    if isinstance(lcr_raw, dict) and lcr_raw.get("id"):
        last_completed_round = {
            "id": str(lcr_raw.get("id", "")),
            "completed_at": str(lcr_raw.get("completed_at", "")),
        }

    rid = str(cur.get("id", "") or "")
    rname = str(cur.get("name", "") or "")
    rstatus = str(cur.get("status", "") or "")
    if rid and rname and rstatus:
        position_label = f"{rid} · {rname}（{rstatus}）"
    elif rid:
        position_label = rid
    else:
        position_label = "未登记（governance/round_state.yaml）"

    next_actions_raw = data.get("next_actions")
    next_actions: list[str] = []
    if isinstance(next_actions_raw, list):
        next_actions = [str(x).strip() for x in next_actions_raw if str(x).strip()]

    roadmap_hint = {
        "current_round_id": rid,
        "current_round_name": rname,
        "current_round_status": rstatus,
        "position_label": position_label,
        "next_actions": next_actions,
        "doc_links": list(DOC_LINKS),
        "state_file": "governance/round_state.yaml",
    }
    return {
        "roadmap_hint": roadmap_hint,
        "last_completed_round": last_completed_round,
    }
