"""FastAPI app: JSON API under /api/v1, plus the built web app (web/dist) when present.

Run: uvicorn dining_planner.api.app:app --reload
"""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .errors import error_response, install_error_handlers
from .routes import meta, recommendations, settings
from .schemas import ErrorResponse

WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "web", "dist")


def create_app(serve_web: bool = True) -> FastAPI:
    app = FastAPI(title="Dining Planner", version="1.0.0", openapi_url="/api/openapi.json", docs_url="/api/docs")
    install_error_handlers(app)

    errors = {status: {"model": ErrorResponse} for status in (409, 422, 502)}
    api = APIRouter(prefix="/api/v1", responses=errors)
    for module in (recommendations, settings, meta):
        api.include_router(module.router)

    @api.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], include_in_schema=False)
    def _unknown_api_route(path: str):
        return error_response(404, "not_found", f"No API route /api/v1/{path}.")

    app.include_router(api)

    if serve_web and os.path.isdir(WEB_DIST):
        _serve_single_page_app(app, WEB_DIST)
    return app


def _serve_single_page_app(app: FastAPI, dist: str) -> None:
    app.mount("/assets", StaticFiles(directory=os.path.join(dist, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def _spa(path: str) -> FileResponse:
        # Real files (favicon etc.) as-is; any other path is a client-side route.
        candidate = os.path.join(dist, path)
        if path and os.path.isfile(candidate) and os.path.commonpath([dist, candidate]) == dist:
            return FileResponse(candidate)
        return FileResponse(os.path.join(dist, "index.html"))


app = create_app()
