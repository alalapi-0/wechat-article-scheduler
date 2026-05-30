"""调度子包骨架，兼容导出既有 scheduler.py 接口。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_LEGACY_PATH = Path(__file__).resolve().parents[1] / "scheduler.py"
_SPEC = importlib.util.spec_from_file_location("wechat_article_scheduler._legacy_scheduler", _LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"无法加载 legacy scheduler 模块: {_LEGACY_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

run_due_jobs = _MODULE.run_due_jobs
scheduler_loop = _MODULE.scheduler_loop

__all__ = ["run_due_jobs", "scheduler_loop"]
