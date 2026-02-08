from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi.errors import RateLimitExceeded

from app import db
from app.config import ENVIRONMENT
from app.rate_limit import limiter
from app.routers import auth, clubs, courts, health, notifications, pages, time_slots
from app.services.baltic_tennis.client import BalticTennisClient
from app.services.baltic_tennis.service import BalticTennisService
from app.services.notifier import notifier
from app.services.registry import registry
from app.services.seb_arena.client import SebArenaClient
from app.services.seb_arena.service import SebArenaService
from app.services.teniso_erdve.client import TenisoErdveClient
from app.services.teniso_erdve.service import TenisoErdveService

_SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


def _load_openapi_spec() -> dict:
    with open(_SPEC_PATH) as f:
        return yaml.safe_load(f)


_openapi_spec = _load_openapi_spec()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    seb_client = SebArenaClient()
    registry.register(SebArenaService(seb_client), seb_client)

    bt_client = BalticTennisClient()
    registry.register(BalticTennisService(bt_client), bt_client)

    te_client = TenisoErdveClient()
    registry.register(TenisoErdveService(te_client), te_client)
    await registry.start()
    await notifier.start()
    yield
    await notifier.stop()
    await registry.stop()
    await db.close_db()


app = FastAPI(
    title=_openapi_spec["info"]["title"],
    description=_openapi_spec["info"]["description"],
    version=_openapi_spec["info"]["version"],
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded: {exc.detail}"},
        )
    return HTMLResponse(
        f"<h2>Too many requests</h2><p>{exc.detail}</p><p>Please wait a moment and try again.</p>",
        status_code=429,
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

if ENVIRONMENT == "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(courts.router)
app.include_router(time_slots.router)
app.include_router(notifications.router)
app.include_router(pages.router)


def custom_openapi():
    return _openapi_spec


app.openapi = custom_openapi  # type: ignore[method-assign]
