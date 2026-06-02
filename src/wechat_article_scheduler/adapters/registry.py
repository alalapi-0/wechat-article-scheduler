"""Adapter registry: capability declarations for multi-platform publish paths.

Existing WeChat runtime selection remains in ``adapters/__init__.py``. This module
lists supported ``platform + adapter_type`` pairs for dry-run, validation, and UI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


class PublishAdapter(Protocol):
    adapter_type: str
    platform: str


@dataclass(frozen=True)
class AdapterKey:
    platform: str
    adapter_type: str


@dataclass(frozen=True)
class AdapterCapability:
    """Declared capability for a platform + adapter_type pair (no secrets)."""

    platform: str
    adapter_type: str
    content_types: tuple[str, ...]
    supports_dry_run: bool
    supports_automated_publish: bool
    requires_human_proof: bool
    risk_level: str  # low | medium | high
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["content_types"] = list(self.content_types)
        return data


_REGISTRY: dict[AdapterKey, type[PublishAdapter]] = {}

BUILTIN_CAPABILITIES: tuple[AdapterCapability, ...] = (
    AdapterCapability(
        platform="wechat_mp",
        adapter_type="official_api",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=False,
        risk_level="medium",
        notes="微信公众号官方 API；真实发布需 WECHAT_MODE=real 与显式开关。",
    ),
    AdapterCapability(
        platform="wechat_mp",
        adapter_type="browser_assist",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="API 缺口字段的人工辅助；不得自动最终发布。",
    ),
    AdapterCapability(
        platform="zhihu",
        adapter_type="manual_export",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="导出 outbox 供人工复制；不登录知乎。",
    ),
    AdapterCapability(
        platform="zhihu",
        adapter_type="browser_assist",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="知乎填表评估 dry-run；不绕过验证码。",
    ),
    AdapterCapability(
        platform="douban",
        adapter_type="manual_export",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="导出 outbox；不登录豆瓣。",
    ),
    AdapterCapability(
        platform="douban",
        adapter_type="browser_assist",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="豆瓣填表评估 dry-run。",
    ),
    AdapterCapability(
        platform="generic",
        adapter_type="manual_export",
        content_types=("article", "note"),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="通用 Markdown/HTML 导出包。",
    ),
    AdapterCapability(
        platform="static_site",
        adapter_type="local_blog",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="静态站 Markdown 输出评估；用户自行 build/deploy。",
    ),
    AdapterCapability(
        platform="wordpress",
        adapter_type="local_blog",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="medium",
        notes="WordPress REST 草稿评估；凭证仅环境变量。",
    ),
    AdapterCapability(
        platform="local_blog",
        adapter_type="local_blog",
        content_types=("article", "note"),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="本地目录写入评估；不触网。",
    ),
    AdapterCapability(
        platform="notification",
        adapter_type="webhook",
        content_types=("article",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="low",
        notes="Webhook 通知；成功不等于平台已发布。",
    ),
    AdapterCapability(
        platform="bilibili",
        adapter_type="manual_export",
        content_types=("video",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="Bilibili 人工上传包（export-outbox --platform bilibili）；不含视频二进制。",
    ),
    AdapterCapability(
        platform="bilibili",
        adapter_type="browser_assist",
        content_types=("video",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="Phase3 预研占位：上传页辅助评估 only。",
    ),
    AdapterCapability(
        platform="wechat_channels",
        adapter_type="manual_export",
        content_types=("video",),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="视频号人工包预研占位；非公众号 API。",
    ),
    AdapterCapability(
        platform="xiaohongshu",
        adapter_type="manual_export",
        content_types=("video", "article"),
        supports_dry_run=True,
        supports_automated_publish=False,
        requires_human_proof=True,
        risk_level="high",
        notes="小红书发布包（export-outbox --platform xiaohongshu）；高风控，仅人工。",
    ),
)


def register_adapter(platform: str, adapter_type: str, adapter_cls: type[PublishAdapter]) -> None:
    _REGISTRY[AdapterKey(platform=platform, adapter_type=adapter_type)] = adapter_cls


def get_registered_adapter(platform: str, adapter_type: str) -> type[PublishAdapter] | None:
    return _REGISTRY.get(AdapterKey(platform=platform, adapter_type=adapter_type))


def list_adapter_capabilities(
    *,
    platform: str | None = None,
    adapter_type: str | None = None,
) -> list[dict[str, Any]]:
    """Return built-in capability rows (sorted), optionally filtered."""
    rows = [c.to_dict() for c in BUILTIN_CAPABILITIES]
    if platform:
        rows = [r for r in rows if r["platform"] == platform]
    if adapter_type:
        rows = [r for r in rows if r["adapter_type"] == adapter_type]
    return sorted(rows, key=lambda r: (r["platform"], r["adapter_type"]))


def capability_for(platform: str, adapter_type: str) -> AdapterCapability | None:
    for cap in BUILTIN_CAPABILITIES:
        if cap.platform == platform and cap.adapter_type == adapter_type:
            return cap
    return None


def is_known_adapter(platform: str, adapter_type: str) -> bool:
    return capability_for(platform, adapter_type) is not None


def infer_platform_from_account_id(platform_account_id: str) -> str | None:
    """Best-effort map manifest target account id to registry platform slug."""
    lower = platform_account_id.lower()
    if "wechat" in lower or lower.startswith("mp_"):
        return "wechat_mp"
    if "zhihu" in lower:
        return "zhihu"
    if "douban" in lower:
        return "douban"
    if lower.startswith("generic"):
        return "generic"
    if "wordpress" in lower or lower.startswith("wp_"):
        return "wordpress"
    if "static" in lower or "hugo" in lower or "jekyll" in lower:
        return "static_site"
    if "blog" in lower:
        return "local_blog"
    if "webhook" in lower or "feishu" in lower or "slack" in lower:
        return "notification"
    if "bilibili" in lower or "b23" in lower:
        return "bilibili"
    if "channels" in lower or "video_account" in lower or "sph" in lower:
        return "wechat_channels"
    if "xiaohongshu" in lower or "xhs" in lower:
        return "xiaohongshu"
    return None
