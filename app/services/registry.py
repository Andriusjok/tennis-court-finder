from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException

from app.generated.models import Club
from app.services.cache import CachedClubService

_REFRESH_INTERVAL = 60.0


class _Closeable(Protocol):
    async def close(self) -> None: ...


class ClubRegistry:
    def __init__(self) -> None:
        self._services: dict[str, CachedClubService] = {}
        self._clients: list[_Closeable] = []

    def register(
        self,
        service: object,
        client: _Closeable,
        *,
        refresh_interval_seconds: float = _REFRESH_INTERVAL,
    ) -> None:
        cached = CachedClubService(
            service,
            refresh_interval_seconds=refresh_interval_seconds,
        )
        club_id = cached.get_club().id
        self._services[club_id] = cached
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
