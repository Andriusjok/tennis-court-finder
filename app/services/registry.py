from __future__ import annotations

from fastapi import HTTPException

from app.generated.models import Club
from app.services.cache import CachedClubService
from app.services.seb_arena.client import SebArenaClient
from app.services.seb_arena.config import CLUB_ID as SEB_ARENA_CLUB_ID
from app.services.seb_arena.service import SebArenaService

_REFRESH_INTERVAL = 60.0


class ClubRegistry:
    def __init__(self) -> None:
        self._services: dict[str, CachedClubService] = {}
        self._clients: list[SebArenaClient] = []

    def register_seb_arena(self) -> None:
        client = SebArenaClient()
        raw_service = SebArenaService(client)
        cached_service = CachedClubService(
            raw_service,
            refresh_interval_seconds=_REFRESH_INTERVAL,
        )
        self._services[SEB_ARENA_CLUB_ID] = cached_service
        self._clients.append(client)

    async def start(self) -> None:
        for service in self._services.values():
            await service.start()

    async def stop(self) -> None:
        for service in self._services.values():
            await service.stop()
        for client in self._clients:
            await client.close()

    def get_service(self, club_id: str) -> CachedClubService | None:
        return self._services.get(club_id)

    def get_service_or_404(self, club_id: str) -> CachedClubService:
        service = self._services.get(club_id)
        if service is None:
            raise HTTPException(status_code=404, detail=f"Club {club_id} not found")
        return service

    def list_clubs(self) -> list[Club]:
        return [svc.get_club() for svc in self._services.values()]


registry = ClubRegistry()
