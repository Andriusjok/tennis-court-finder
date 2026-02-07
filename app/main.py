"""
FastAPI application factory.

The app serves Swagger UI at /docs and ReDoc at /redoc, both driven by
the hand-crafted openapi.yaml specification. Route handlers import
auto-generated Pydantic models from app.generated.models.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import db
from app.config import ENVIRONMENT
from app.rate_limit import limiter
from app.routers import auth, clubs, courts, health, notifications, pages, time_slots
from app.services.notifier import notifier
from app.services.registry import registry

# ── Load the hand-crafted OpenAPI spec ────────────────────────────────────
_SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


def _load_openapi_spec() -> dict:
    with open(_SPEC_PATH) as f:
        return yaml.safe_load(f)


_openapi_spec = _load_openapi_spec()


# ── Lifespan: startup / shutdown ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.init_db()
    registry.register_seb_arena()
    await registry.start()
    await notifier.start()
    yield
    # Shutdown
    await notifier.stop()
    await registry.stop()
    await db.close_db()


# ── App factory ───────────────────────────────────────────────────────────

app = FastAPI(
    title=_openapi_spec["info"]["title"],
    description=_openapi_spec["info"]["description"],
    version=_openapi_spec["info"]["version"],
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
    lifespan=lifespan,
)

# ── Rate limiting ─────────────────────────────────────────────────────────
app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return JSON for API routes, HTML for browser pages."""
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )
    return HTMLResponse(
        f"<h2>Too many requests</h2><p>{exc.detail}</p>"
        "<p>Please wait a moment and try again.</p>",
        status_code=429,
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# ── CORS ──────────────────────────────────────────────────────────────────
if ENVIRONMENT == "production":
    # In production, restrict to same-origin only (UI is served from the app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
else:
    # Permissive for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Register routers ─────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(courts.router)
app.include_router(time_slots.router)
app.include_router(notifications.router)
app.include_router(pages.router)          # HTML pages (HTMX + Jinja2)


# ── Override OpenAPI schema with the hand-crafted spec ────────────────────
def custom_openapi():
    """
    Return the hand-crafted openapi.yaml as the schema for /docs and /redoc.

    FastAPI normally auto-generates the schema from route decorators.
    We override this so the Swagger UI is driven by our spec-first YAML,
    while the route handlers ensure the implementation matches.
    """
    return _openapi_spec


app.openapi = custom_openapi  # type: ignore[method-assign]
