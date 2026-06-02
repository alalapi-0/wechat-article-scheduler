"""Future manifest loader placeholder.

The current scan/upload flow remains the source of truth for WeChat articles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a publish_manifest.json draft without importing it into the DB."""
    return json.loads(path.read_text(encoding="utf-8"))
