"""Local Web request boundary for state-changing operations."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

_STATE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_LOOPBACK_NAMES = frozenset({"localhost", "testserver"})


def _authority_parts(value: str, *, scheme: str) -> tuple[str, int] | None:
    """Parse a Host header as an authority, never as a URL."""
    if not value or value != value.strip() or any(ch in value for ch in "\r\n,\\/?#@"):
        return None
    try:
        parsed = urlsplit(f"//{value}")
        if parsed.username or parsed.password or not parsed.hostname or parsed.path:
            return None
        port = parsed.port or (443 if scheme == "https" else 80)
        return parsed.hostname.lower(), port
    except ValueError:
        return None


def _url_authority(value: str, *, allow_path: bool) -> tuple[str, str, int] | None:
    """Parse Origin/Referer while keeping their different path contracts explicit."""
    if not value or value != value.strip() or any(ch in value for ch in "\r\n"):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or parsed.password
            or not parsed.hostname
            or parsed.fragment
            or (not allow_path and (parsed.path or parsed.query))
        ):
            return None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return parsed.scheme, parsed.hostname.lower(), port
    except ValueError:
        return None


def _is_loopback_host(host: str) -> bool:
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def install_local_request_boundary(app: object) -> None:
    @app.middleware("http")
    async def enforce_local_state_change(request: Request, call_next):
        host_values = request.headers.getlist("host")
        if len(host_values) != 1:
            return JSONResponse(status_code=400, content={"detail": "Host 头必须唯一"})
        host_parts = _authority_parts(host_values[0], scheme=request.url.scheme)
        host_allowed = host_parts is not None and _is_loopback_host(host_parts[0])
        if host_parts is not None and host_parts[0] == "testserver":
            host_allowed = bool(request.client and request.client.host == "testclient")
        if not host_allowed:
            return JSONResponse(status_code=400, content={"detail": "Host 必须是本机回环地址"})
        if request.method.upper() not in _STATE_METHODS:
            return await call_next(request)
        fetch_site = (request.headers.get("sec-fetch-site") or "").strip().lower()
        if fetch_site in {"cross-site", "same-site"}:
            return JSONResponse(status_code=403, content={"detail": "已拒绝跨站状态变更请求"})
        for header in ("origin", "referer"):
            raw = request.headers.get(header)
            if raw is None:
                continue
            actual = _url_authority(raw, allow_path=header == "referer")
            if (
                raw.strip().lower() == "null"
                or actual is None
                or actual[0] != request.url.scheme
                or actual[1:] != host_parts
            ):
                return JSONResponse(status_code=403, content={"detail": "已拒绝跨站状态变更请求"})
        return await call_next(request)
