"""FastAPI application entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import Base, engine
from app.limiter import limiter
from app.routers import admin, chat, customers, widgets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs",
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# --- CORS ---
# The chat endpoint enforces per-website domain validation itself; CORS here is
# permissive for the browser preflight but real authorization happens in code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(chat.router)
app.include_router(widgets.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup() -> None:
    # In production, migrations are managed by Alembic. create_all is a safety
    # net for fresh dev environments and is idempotent.
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


# --- Serve widget assets directly (single-service deploys without Nginx) ---
_assets_dir = Path(settings.widget_assets_dir) if settings.widget_assets_dir else None
if _assets_dir and _assets_dir.is_dir():

    @app.get("/widget.js", include_in_schema=False)
    def widget_js() -> FileResponse:
        return FileResponse(
            _assets_dir / "widget.js",
            media_type="application/javascript",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=300",
            },
        )

    @app.get("/demo.html", include_in_schema=False)
    def demo_html() -> FileResponse:
        return FileResponse(_assets_dir / "demo.html", media_type="text/html")
