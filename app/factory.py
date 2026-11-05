"""Fabrique de l'application FastAPI (importée par app/main.py et par les tests)."""

from __future__ import annotations

import logging
from pathlib import Path

import plotly
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, dashboard, data, datasets
from app.config import FRONTEND_DIR, LOCALES_DIR, Settings, get_settings
from app.state import KitState

__version__ = "0.1.1"
PLOTLY_JS = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    app.state.kit = KitState.create(settings)

    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "DELETE"],
                           allow_headers=["Authorization", "Content-Type"])
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):  # pragma: no cover
        logging.getLogger("kit").exception("Erreur inattendue sur %s", request.url.path)
        return JSONResponse({"detail": "Erreur interne du serveur"}, status_code=500)

    for router in (auth.router, dashboard.router, datasets.router, data.router):
        app.include_router(router)

    @app.get("/api/health", include_in_schema=False)
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    @app.get("/vendor/plotly.min.js", include_in_schema=False)
    def plotly_js() -> FileResponse:
        # Servi localement : le tableau de bord fonctionne sans accès Internet.
        return FileResponse(PLOTLY_JS, media_type="application/javascript",
                            headers={"Cache-Control": "public, max-age=604800"})

    app.mount("/locales", StaticFiles(directory=LOCALES_DIR), name="locales")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    return app
