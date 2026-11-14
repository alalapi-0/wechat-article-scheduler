"""微信公众号 API 能力探测（区分未授权 / 空列表 / 请求失败）。"""

from __future__ import annotations

import json
import urllib.error
from datetime import datetime, timezone
from typing import Any

from wechat_article_scheduler.adapters.wechat_http import WechatApiError
from wechat_article_scheduler.external_agent.redaction import redact_sensitive_values
from wechat_article_scheduler.wechat_errors import wechat_error_diagnostic

CAPABILITY_DRAFT_LIST = "draft_batchget"
CAPABILITY_PUBLISHED_LIST = "freepublish_batchget"


def _classify_probe_response(
    data: dict[str, Any] | None,
    *,
    exc: Exception | None,
    list_key: str,
) -> dict[str, Any]:
    """将 API 响应归类为 authorized / unauthorized / empty / error。"""
    if exc is not None:
        if isinstance(exc, WechatApiError):
            return {
                "state": "unauthorized" if exc.errcode == 48001 else "error",
                "item_count": None,
                "error_code": exc.errcode,
                **wechat_error_diagnostic(exc.errcode),
            }
        network = isinstance(exc, (urllib.error.URLError, OSError))
        return {
            "state": "error",
            "message": "请求失败：网络连接异常" if network else "请求失败：未完成接口读取",
            "item_count": None,
            "error_code": None,
            "reason_code": "network_error" if network else "request_error",
            "action_hint": "核对连接后人工决定是否重试" if network else "核对本地配置和接口响应；不推断端点权限",
        }
    if not data:
        return {
            "state": "error",
            "message": "请求失败：空响应",
            "item_count": None,
            "reason_code": "empty_response",
            "action_hint": "核对接口响应；空响应不表示空列表或未授权",
        }
    try:
        errcode = int(data.get("errcode", 0) or 0)
    except (TypeError, ValueError):
        return {
            "state": "error",
            "message": "请求失败：错误码格式无效",
            "item_count": None,
            "reason_code": "invalid_response",
            "action_hint": "核对接口响应；不推断端点权限",
        }
    if errcode != 0:
        return {
            "state": "unauthorized" if errcode == 48001 else "error",
            "item_count": None,
            "error_code": errcode,
            **wechat_error_diagnostic(errcode),
        }
    items = data.get(list_key)
    if isinstance(items, list):
        count = len(items)
        if count == 0:
            return {
                "state": "empty",
                "message": "接口已授权，当前列表为空",
                "item_count": 0,
            }
        return {
            "state": "authorized",
            "message": f"接口已授权，当前页 {count} 条",
            "item_count": count,
        }
    total = data.get("total_count")
    if total is not None:
        tc = int(total)
        if tc == 0:
            return {
                "state": "empty",
                "message": "接口已授权，当前列表为空",
                "item_count": 0,
            }
        return {
            "state": "authorized",
            "message": f"接口已授权，共 {tc} 条",
            "item_count": tc,
        }
    return {
        "state": "authorized",
        "message": "接口已授权",
        "item_count": None,
    }


def probe_draft_batchget(adapter: Any) -> dict[str, Any]:
    """探测 draft/batchget 列表权限。"""
    try:
        data = adapter.list_drafts_batchget(offset=0, count=1)
        result = _classify_probe_response(data, exc=None, list_key="item")
    except Exception as exc:  # noqa: BLE001
        result = _classify_probe_response(None, exc=exc, list_key="item")
    result["capability_id"] = CAPABILITY_DRAFT_LIST
    result["label"] = "草稿箱列表 (draft/batchget)"
    return result


def probe_freepublish_batchget(adapter: Any) -> dict[str, Any]:
    """探测 freepublish/batchget 列表权限。"""
    try:
        data = adapter.list_published_batchget(offset=0, count=1)
        result = _classify_probe_response(data, exc=None, list_key="item")
    except Exception as exc:  # noqa: BLE001
        result = _classify_probe_response(None, exc=exc, list_key="item")
    result["capability_id"] = CAPABILITY_PUBLISHED_LIST
    result["label"] = "已发布列表 (freepublish/batchget)"
    return result


def probe_all_capabilities(adapter: Any) -> dict[str, Any]:
    """探测草稿与已发布列表能力。"""
    drafts = probe_draft_batchget(adapter)
    published = probe_freepublish_batchget(adapter)
    return {
        "draft_list": drafts,
        "published_list": published,
        "probed_at": datetime.now(timezone.utc).isoformat(),
    }


def _redact_raw(data: dict[str, Any]) -> str:
    safe = redact_sensitive_values({
        key: data[key]
        for key in (
            "capability_id", "state", "message", "item_count", "error_code",
            "reason_code", "action_hint", "label",
        )
        if key in data
    })
    return json.dumps(safe, ensure_ascii=False)


def cache_capability_probe(conn: Any, probe: dict[str, Any]) -> None:
    """将探测结果写入 wechat_capability_cache。"""
    cap_id = probe.get("capability_id") or "unknown"
    conn.execute(
        """
        INSERT INTO wechat_capability_cache
            (capability_id, state, message, item_count, probed_at, raw_redacted)
        VALUES (?, ?, ?, ?, datetime('now'), ?)
        ON CONFLICT(capability_id) DO UPDATE SET
            state = excluded.state,
            message = excluded.message,
            item_count = excluded.item_count,
            probed_at = excluded.probed_at,
            raw_redacted = excluded.raw_redacted
        """,
        (
            cap_id,
            probe.get("state", "error"),
            probe.get("message", ""),
            probe.get("item_count"),
            _redact_raw(probe),
        ),
    )


def get_cached_capabilities(conn: Any) -> dict[str, Any]:
    """读取缓存的能力探测结果。"""
    rows = conn.execute(
        "SELECT capability_id, state, message, item_count, probed_at, raw_redacted FROM wechat_capability_cache"
    ).fetchall()
    out: dict[str, Any] = {}
    for row in rows:
        out[str(row["capability_id"])] = {
            "state": row["state"],
            "message": row["message"],
            "item_count": row["item_count"],
            "probed_at": row["probed_at"],
        }
        try:
            raw = json.loads(row["raw_redacted"] or "{}")
        except (TypeError, ValueError):
            raw = {}
        if isinstance(raw, dict):
            for key in ("reason_code", "action_hint", "error_code"):
                if key in raw:
                    out[str(row["capability_id"])][key] = raw[key]
    return out


def human_capability_summary(cached: dict[str, Any]) -> dict[str, str]:
    """普通视图用的人话摘要。"""
    pub = cached.get(CAPABILITY_PUBLISHED_LIST, {})
    state = pub.get("state", "unknown")
    if state == "unauthorized":
        return {"published_list": "未授权：无法读取已发布文章列表"}
    if state == "empty":
        return {"published_list": "已授权，当前无已发布文章"}
    if state == "authorized":
        cnt = pub.get("item_count")
        label = f"已授权，约 {cnt} 条" if cnt is not None else "已授权"
        return {"published_list": label}
    if state == "error":
        return {"published_list": pub.get("message", "探测失败")}
    return {"published_list": "尚未探测"}
