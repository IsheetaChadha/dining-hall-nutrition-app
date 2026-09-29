"""Every API error is `{"error": {"code", "message", "fields"?}}` so clients can switch on `code`."""

from __future__ import annotations

from typing import Optional

import requests
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ..service import CalendarNotConfiguredError, UpstreamUnavailableError

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_response(status: int, code: str, message: str, fields: Optional[dict[str, str]] = None) -> JSONResponse:
    body = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return JSONResponse(status_code=status, content={"error": body})


def _field_path(loc: tuple) -> str:
    """("body", "building_coords", "WALC", 0) -> "building_coords.WALC"; tuple indexes are dropped."""
    parts = [str(p) for p in loc[1:] if not isinstance(p, int)]
    return ".".join(parts) or "body"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            fields.setdefault(_field_path(err["loc"]), err["msg"].removeprefix("Value error, "))
        code = "invalid_settings" if request.url.path.endswith("/settings") else "invalid_request"
        return error_response(422, code, "Some values aren't valid.", fields)

    @app.exception_handler(CalendarNotConfiguredError)
    async def _no_calendar(request: Request, exc: CalendarNotConfiguredError) -> JSONResponse:
        return error_response(
            409,
            "calendar_not_configured",
            "No calendar is connected. Save your calendar's private iCal URL to credentials/calendar_url.txt, "
            "or add Google OAuth credentials at credentials/client_secret.json.",
        )

    @app.exception_handler(UpstreamUnavailableError)
    async def _upstream(request: Request, exc: UpstreamUnavailableError) -> JSONResponse:
        return error_response(502, "upstream_unavailable", str(exc))

    @app.exception_handler(requests.RequestException)
    async def _upstream_http(request: Request, exc: requests.RequestException) -> JSONResponse:
        return error_response(502, "upstream_unavailable", "Couldn't reach Purdue Dining. Try again in a moment.")

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(exc.status_code, _HTTP_CODES.get(exc.status_code, "http_error"), str(exc.detail))
