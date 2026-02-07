"""
Club service registry – holds all integrated club services.

Provides a single place to look up a club service by club_id.
Initialized once at application startup.

Every raw service is wrapped in a CachedClubService so the external
booking APIs are only polled on a fixed schedule, not per-request.
"""

from __future__ import annotations

from app.generated.models import Club
from app.services.cache import CachedClubService
from app.services.seb_arena.client import SebArenaClient
from app.services.seb_arena.config import CLUB_ID as SEB_ARENA_CLUB_ID
from app.services.seb_arena.service import SebArenaService

# Default cache refresh interval (seconds)
_REFRESH_INTERVAL = 60.0


class ClubRegistry:
    """
    Registry of all integrated tennis club services.

    Each club service is registered by its slug (e.g. "seb-arena") and
    can be looked up at runtime by the routers.
    """

    def __init__(self) -> None:
        self._services: dict[str, CachedClubService] = {}
        self._clients: list[SebArenaClient] = []

    def register_seb_arena(self) -> None:
        """Initialize and register the SEB Arena integration."""
        client = SebArenaClient()
        raw_service = SebArenaService(client)
        cached_service = CachedClubService(
            raw_service,
            refresh_interval_seconds=_REFRESH_INTERVAL,
        )
        self._services[SEB_ARENA_CLUB_ID] = cached_service
        self._clients.append(client)

    async def start(self) -> None:
        """Start the background cache refresh for all registered services."""
        for service in self._services.values():
            await service.start()

    async def stop(self) -> None:
        """Stop background tasks and close all HTTP clients."""
        for service in self._services.values():
            await service.stop()
        for client in self._clients:
            await client.close()

    def get_service(self, club_id: str) -> CachedClubService | None:
        """Get the service for a given club slug."""
        return self._services.get(club_id)

    def list_clubs(self) -> list[Club]:
        """Return metadata for all registered clubs."""
        return [svc.get_club() for svc in self._services.values()]


# ── Singleton instance ────────────────────────────────────────────────────
registry = ClubRegistry()
