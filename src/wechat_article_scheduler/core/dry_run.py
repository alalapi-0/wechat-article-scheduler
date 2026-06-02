"""Future dry-run result primitives."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    messages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DryRunResult:
    ok: bool
    report: dict
    preview_html: str = ""
