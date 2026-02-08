from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from app.generated.models import Club, Court, TimeSlot
from app.services.background import BackgroundWorker

logger = logging.getLogger(__name__)

_DEFAULT_FETCH_DAYS = 8


class SlotCache:
    def __init__(self) -> None:
        self._courts: list[Court] = []
        self._slots: list[TimeSlot] = []
        self._last_refresh: datetime | None = None

    def update(self, courts: list[Court], slots: list[TimeSlot]) -> None:
        self._courts = list(courts)
        self._slots = list(slots)
        self._last_refresh = datetime.now(UTC)
        logger.info(
            "Cache updated: %d courts, %d slots (at %s)",
            len(self._courts),
            len(self._slots),
            self._last_refresh.isoformat(),
        )

    @property
    def is_populated(self) -> bool:
        return self._last_refresh is not None

    @property
    def last_refresh(self) -> datetime | None:
        return self._last_refresh

    def get_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]:
        courts = self._courts
        if surface_type:
            courts = [c for c in courts if c.surface_type == surface_type]
        if court_type:
            courts = [c for c in courts if c.court_type == court_type]
        return courts

    def get_court(self, court_id: str) -> Court | None:
        target = UUID(court_id) if isinstance(court_id, str) else court_id
        for court in self._courts:
            if court.id == target:
                return court
        return None

    def get_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]:
        slots = [s for s in self._slots if date_from <= s.start_time.date() <= date_to]

        if court_id:
            target = UUID(court_id) if isinstance(court_id, str) else court_id
            slots = [s for s in slots if s.court_id == target]
        if status:
            slots = [s for s in slots if s.status == status]
        if surface_type:
            slots = [s for s in slots if s.surface_type == surface_type]
        if court_type:
            slots = [s for s in slots if s.court_type == court_type]

        return slots


class CachedClubService(BackgroundWorker):
    def __init__(
        self,
        delegate: object,
        *,
        refresh_interval_seconds: float = 60.0,
        fetch_days: int = _DEFAULT_FETCH_DAYS,
    ) -> None:
        club_id = delegate.get_club().id
        super().__init__(interval=refresh_interval_seconds, name=f"cache-{club_id}")
        self._delegate = delegate
        self._cache = SlotCache()
        self._fetch_days = fetch_days

    async def _on_start(self) -> None:
        await self._refresh()

    async def _tick(self) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        logger.info("[%s] Refreshing cache from upstream...", self._name)
        today = date.today()
        date_to = today + timedelta(days=self._fetch_days - 1)
        courts = await self._delegate.list_courts()
        slots = await self._delegate.list_time_slots(date_from=today, date_to=date_to)
        self._cache.update(courts, slots)
        logger.info("[%s] Cache ready: %d courts, %d slots", self._name, len(courts), len(slots))

    def get_club(self) -> Club:
        return self._delegate.get_club()

    async def list_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]:
        if not self._cache.is_populated:
            return await self._delegate.list_courts(
                surface_type=surface_type,
                court_type=court_type,
            )
        return self._cache.get_courts(surface_type=surface_type, court_type=court_type)

    async def get_court(self, court_id: str) -> Court | None:
        if not self._cache.is_populated:
            return await self._delegate.get_court(court_id)
        return self._cache.get_court(court_id)

    async def list_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]:
        if not self._cache.is_populated:
            return await self._delegate.list_time_slots(
                date_from=date_from,
                date_to=date_to,
                court_id=court_id,
                status=status,
                surface_type=surface_type,
                court_type=court_type,
            )
        return self._cache.get_time_slots(
            date_from=date_from,
            date_to=date_to,
            court_id=court_id,
            status=status,
            surface_type=surface_type,
            court_type=court_type,
        )

    @property
    def last_refresh(self) -> datetime | None:
        return self._cache.last_refresh
