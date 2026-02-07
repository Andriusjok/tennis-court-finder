"""
Shared test fixtures.

Provides a FastAPI TestClient wired to mock services so unit tests
never hit external APIs.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.services.registry import ClubRegistry, registry
from tests.mocks.models import MOCK_CLUB, MOCK_CLUB_2, MOCK_USER
from tests.mocks.services import MockClubService


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_registry(monkeypatch: pytest.MonkeyPatch) -> ClubRegistry:
    """
    Replace the global registry with one backed by MockClubService.
    Restores the original registry after the test.
    """
    test_registry = ClubRegistry()

    # Register mock services
    mock_service = MockClubService(club=MOCK_CLUB)
    test_registry._services[MOCK_CLUB.id] = mock_service
    test_registry._clients = []

    mock_service_2 = MockClubService(club=MOCK_CLUB_2, courts=[], time_slots=[])
    test_registry._services[MOCK_CLUB_2.id] = mock_service_2

    # Monkey-patch the module-level singleton
    import app.services.registry as reg_mod

    monkeypatch.setattr(reg_mod, "registry", test_registry)

    # Also patch the already-imported references in routers
    import app.routers.clubs as clubs_mod
    import app.routers.courts as courts_mod
    import app.routers.time_slots as ts_mod

    monkeypatch.setattr(clubs_mod, "registry", test_registry)
    monkeypatch.setattr(courts_mod, "registry", test_registry)
    monkeypatch.setattr(ts_mod, "registry", test_registry)

    return test_registry


@pytest.fixture()
def client(mock_registry: ClubRegistry) -> TestClient:
    """
    FastAPI TestClient with mock services and no auth requirement.
    """
    # Override auth dependency to always return mock user
    async def _mock_current_user():
        return MOCK_USER

    app.dependency_overrides[get_current_user] = _mock_current_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture()
def unauthed_client(mock_registry: ClubRegistry) -> TestClient:
    """
    FastAPI TestClient without auth overrides — requests will be rejected
    unless a session cookie is provided.
    """
    app.dependency_overrides.clear()
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()
