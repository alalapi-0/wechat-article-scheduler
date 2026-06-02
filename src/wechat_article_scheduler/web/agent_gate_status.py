"""只读暴露 agent_gate status 摘要（供 /api/agent-gate-status）。"""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from typing import Any

from wechat_article_scheduler.config import ROOT


@lru_cache(maxsize=1)
def _agent_gate_module() -> Any:
    path = ROOT / "scripts" / "agent_gate.py"
    spec = importlib.util.spec_from_file_location("agent_gate_web", path)
    if not spec or not spec.loader:
        raise RuntimeError("agent_gate.py not loadable")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["agent_gate_web"] = mod
    spec.loader.exec_module(mod)
    return mod


def build_agent_gate_status_api() -> dict[str, Any]:
    """与 CLI ``agent_gate status --json`` 同结构的只读字段。"""
    return _agent_gate_module().build_status_payload()
