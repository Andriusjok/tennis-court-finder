from __future__ import annotations

from datetime import date
from typing import Protocol

from app.generated.models import Club, Court, TimeSlot


class TennisClubService(Protocol):
    def get_club(self) -> Club: ...

    async def list_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]: ...

    async def get_court(self, court_id: str) -> Court | None: ...

    async def list_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]: ...
