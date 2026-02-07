"""
FastAPI application factory.

The app serves Swagger UI at /docs and ReDoc at /redoc, both driven by
the hand-crafted openapi.yaml specification. Route handlers import
auto-generated Pydantic models from app.generated.models.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, clubs, courts, health, notifications, pages, time_slots
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
    # Startup: register club integrations and start background cache refresh
    registry.register_seb_arena()
    await registry.start()
    yield
    # Shutdown: stop background tasks and close HTTP clients
    await registry.stop()


# ── App factory ───────────────────────────────────────────────────────────

app = FastAPI(
    title=_openapi_spec["info"]["title"],
    description=_openapi_spec["info"]["description"],
    version=_openapi_spec["info"]["version"],
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc
    lifespan=lifespan,
)

# ── CORS (permissive for local dev) ───────────────────────────────────────
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
