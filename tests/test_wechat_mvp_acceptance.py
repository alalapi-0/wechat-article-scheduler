"""Round 76 / 收敛 Round 21：MVP 闭环验收清单。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "wechat_mvp_acceptance.md"
ROADMAP = ROOT / "docs" / "roadmap_converged.md"


def test_mvp_acceptance_doc_exists() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "闭环" in text
    assert "proof" in text.lower() or "proof" in text
    assert "WECHAT_MODE=mock" in text


def test_roadmap_round_21_present() -> None:
    text = ROADMAP.read_text(encoding="utf-8")
    assert "Round 21" in text
    assert "闭环验收" in text


def test_core_modules_importable() -> None:
    from wechat_article_scheduler import publish_policy  # noqa: F401
    from wechat_article_scheduler.review import proof  # noqa: F401
    from wechat_article_scheduler.adapters.browser_assist import workflow  # noqa: F401
    from wechat_article_scheduler import wechat_field_matrix  # noqa: F401
