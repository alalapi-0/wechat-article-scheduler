"""Future adapter registry draft.

Existing WeChat adapter selection still lives in adapters/__init__.py. This registry
is a non-invasive skeleton for future multi-platform adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PublishAdapter(Protocol):
    adapter_type: str
    platform: str


@dataclass(frozen=True)
class AdapterKey:
    platform: str
    adapter_type: str


_REGISTRY: dict[AdapterKey, type[PublishAdapter]] = {}


def register_adapter(platform: str, adapter_type: str, adapter_cls: type[PublishAdapter]) -> None:
    _REGISTRY[AdapterKey(platform=platform, adapter_type=adapter_type)] = adapter_cls


def get_registered_adapter(platform: str, adapter_type: str) -> type[PublishAdapter] | None:
    return _REGISTRY.get(AdapterKey(platform=platform, adapter_type=adapter_type))
