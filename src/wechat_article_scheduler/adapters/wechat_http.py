"""微信公众平台 HTTP 工具（仅 WECHAT_MODE=real 时使用）。"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

logger = logging.getLogger(__name__)

API_BASE = "https://api.weixin.qq.com"


class WechatApiError(RuntimeError):
    """微信 API 返回 errcode != 0 时抛出。"""

    def __init__(self, errcode: int, errmsg: str, *, endpoint: str = "") -> None:
        self.errcode = errcode
        self.errmsg = errmsg
        self.endpoint = endpoint
        super().__init__(f"微信 API 错误 {errcode}: {errmsg} ({endpoint})")


class TokenCache:
    """
    access_token 内存缓存（约 2 小时有效，提前 60 秒刷新）。

    缓存仅存内存，不落盘、不写日志。
    """

    def __init__(self, refresh_skew_seconds: int = 60) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._refresh_skew = refresh_skew_seconds

    def clear(self) -> None:
        """清空缓存（测试或凭证变更时使用）。"""
        self._token = None
        self._expires_at = 0.0

    def get_token(self, fetcher: Callable[[], dict[str, Any]]) -> str:
        """返回有效 token；过期时调用 fetcher 刷新。"""
        now = time.time()
        if self._token and now < self._expires_at - self._refresh_skew:
            return self._token
        data = fetcher()
        token = str(data.get("access_token", ""))
        if not token:
            raise WechatApiError(-1, "access_token 缺失", endpoint="token")
        expires_in = int(data.get("expires_in", 7200))
        self._token = token
        self._expires_at = now + max(60, expires_in)
        return self._token


def redact_url(url: str, secret: str = "") -> str:
    """日志用 URL 脱敏（隐藏 secret / access_token）。"""
    out = url
    if secret:
        out = out.replace(secret, "***REDACTED***")
    if "access_token=" in out:
        parsed = urllib.parse.urlsplit(out)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if "access_token" in qs:
            qs["access_token"] = ["***REDACTED***"]
            out = urllib.parse.urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    urllib.parse.urlencode(qs, doseq=True),
                    parsed.fragment,
                )
            )
    return out


def _check_response(data: dict[str, Any], *, endpoint: str) -> dict[str, Any]:
    """检查 errcode 字段（0 或缺失视为成功）。"""
    errcode = data.get("errcode")
    if errcode is not None and int(errcode) != 0:
        raise WechatApiError(int(errcode), str(data.get("errmsg", "")), endpoint=endpoint)
    return data


def http_get_json(url: str, *, timeout: float = 30.0) -> dict[str, Any]:
    """GET 请求并解析 JSON。"""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise WechatApiError(exc.code, body[:200], endpoint=url.split("?")[0]) from exc
    data = json.loads(raw)
    return _check_response(data, endpoint=url.split("?")[0])


def http_post_json(url: str, body: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    """POST JSON 并解析响应。"""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise WechatApiError(exc.code, body_text[:200], endpoint=url.split("?")[0]) from exc
    data = json.loads(raw)
    return _check_response(data, endpoint=url.split("?")[0])


def build_multipart(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """构造 multipart/form-data 请求体（用于素材上传）。"""
    boundary = f"----WechatScheduler{int(time.time() * 1000)}"
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(value.encode("utf-8"))
        lines.append(b"\r\n")
    for name, (filename, content, content_type) in files.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        lines.append(content)
        lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def http_post_multipart(
    url: str,
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST multipart 表单（上传 thumb 等素材）。"""
    body, content_type = build_multipart(fields, files)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise WechatApiError(exc.code, body_text[:200], endpoint=url.split("?")[0]) from exc
    data = json.loads(raw)
    return _check_response(data, endpoint=url.split("?")[0])
