"""Request-scoped multipart limits for cover uploads.

Starlette's ``max_part_size`` applies only to ordinary form fields.  Cover files
therefore need a parser callback limit so oversized bytes are rejected before
they are queued for writes to ``SpooledTemporaryFile``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException, MultiPartParser, parse_options_header
from starlette.requests import Request

from wechat_article_scheduler.cover_assets.index import MAX_COVER_BYTES


class CoverUploadTooLarge(MultiPartException):
    pass


class CoverLimitedMultiPartParser(MultiPartParser):
    """Apply one aggregate byte budget to the ``cover``/``covers`` file fields."""

    def __init__(self, *args: Any, cover_max_bytes: int, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cover_max_bytes = cover_max_bytes
        self.cover_bytes = 0

    def on_part_data(self, data: bytes, start: int, end: int) -> None:
        part_bytes = end - start
        if (
            self._current_part.file is not None
            and self._current_part.field_name in {"cover", "covers"}
        ):
            if self.cover_bytes + part_bytes > self.cover_max_bytes:
                raise CoverUploadTooLarge(
                    f"封面上传数据不能超过 {self.cover_max_bytes // (1024 * 1024)} MB"
                )
            self.cover_bytes += part_bytes
        super().on_part_data(data, start, end)


class CoverLimitedRoute(APIRoute):
    """Use the cover-aware parser without changing Starlette process globals."""

    cover_max_bytes = MAX_COVER_BYTES

    def get_route_handler(self) -> Callable[[Request], Awaitable[Any]]:
        route_handler = super().get_route_handler()

        async def limited_route_handler(request: Request) -> Any:
            original_get_form = request._get_form

            async def limited_get_form(
                *,
                max_files: int | float = 1000,
                max_fields: int | float = 1000,
                max_part_size: int = 1024 * 1024,
            ):
                if request._form is not None:
                    return request._form
                content_type, _params = parse_options_header(
                    request.headers.get("content-type", "")
                )
                if content_type != b"multipart/form-data":
                    return await original_get_form(
                        max_files=max_files,
                        max_fields=max_fields,
                        max_part_size=max_part_size,
                    )
                parser = CoverLimitedMultiPartParser(
                    request.headers,
                    request.stream(),
                    max_files=max_files,
                    max_fields=max_fields,
                    max_part_size=max_part_size,
                    cover_max_bytes=self.cover_max_bytes,
                )
                try:
                    request._form = await parser.parse()
                except CoverUploadTooLarge as exc:
                    raise HTTPException(status_code=413, detail=exc.message) from exc
                except MultiPartException as exc:
                    raise HTTPException(status_code=400, detail=exc.message) from exc
                return request._form

            request._get_form = limited_get_form  # type: ignore[method-assign]
            return await route_handler(request)

        return limited_route_handler
