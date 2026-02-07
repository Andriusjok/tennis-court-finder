"""
Shared test fixtures.

Provides a FastAPI TestClient wired to:
  • mock club services (no external HTTP)
  • a temporary SQLite database (via app lifespan)
  • a no-op notifier

The `client` fixture runs the full lifespan (DB init / shutdown) so that
notification endpoints backed by SQLite work correctly in tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.services.registry import ClubRegistry
from tests.mocks.models import MOCK_CLUB, MOCK_CLUB_2, MOCK_USER
from tests.mocks.services import MockClubService


# ── Helpers ────────────────────────────────────────────────────────────────


class _NoopNotifier:
    """Drop-in replacement for SlotNotifier that does nothing."""

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def _test_env(monkeypatch, tmp_path):
    """
    Internal fixture that patches the DB path, registry, and notifier
    so that the app lifespan runs cleanly against a temp database and
    mock services.
    """
    # ── Temp database ─────────────────────────────────────────────────
    import app.db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", str(tmp_path / "test.db"))

    # ── Mock club registry ────────────────────────────────────────────
    test_registry = ClubRegistry()

    svc1 = MockClubService(club=MOCK_CLUB)
    test_registry._services[MOCK_CLUB.id] = svc1
    test_registry._clients = []

    svc2 = MockClubService(club=MOCK_CLUB_2, courts=[], time_slots=[])
    test_registry._services[MOCK_CLUB_2.id] = svc2

    # Prevent the lifespan from registering real services
    test_registry.register_seb_arena = lambda: None  # type: ignore[assignment]

    # Patch everywhere `registry` was imported
    for mod_path in (
        "app.services.registry",
        "app.main",
        "app.routers.clubs",
        "app.routers.courts",
        "app.routers.time_slots",
        "app.routers.pages",
        "app.services.notifier",
    ):
        monkeypatch.setattr(f"{mod_path}.registry", test_registry)

    # ── No-op notifier ────────────────────────────────────────────────
    monkeypatch.setattr("app.main.notifier", _NoopNotifier())

    # ── Disable rate limiting in tests ────────────────────────────────
    from app.rate_limit import limiter as _limiter
    monkeypatch.setattr(_limiter, "enabled", False)

    return test_registry


@pytest.fixture()
def mock_registry(_test_env) -> ClubRegistry:
    """Public alias for tests that reference mock_registry directly."""
    return _test_env


@pytest.fixture()
def client(_test_env: ClubRegistry) -> TestClient:
    """
    FastAPI TestClient with mock services, temp DB, and auth bypassed.

    Uses a context manager so the lifespan runs (DB init/shutdown).
    """
    async def _mock_current_user():
        return MOCK_USER

    app.dependency_overrides[get_current_user] = _mock_current_user

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc

    app.dependency_overrides.clear()


@pytest.fixture()
def unauthed_client(_test_env: ClubRegistry) -> TestClient:
    """
    TestClient without auth overrides — requests are rejected unless
    a session cookie is provided.
    """
    app.dependency_overrides.clear()

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc

    app.dependency_overrides.clear()
