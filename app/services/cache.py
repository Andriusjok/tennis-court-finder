"""
Caching layer for tennis club services.

Wraps any TennisClubService with an in-memory cache that is periodically
refreshed by a background task.  API requests are served from the cache
so the external booking system is only hit once per refresh cycle.

Usage::

    service = SebArenaService(client)
    cached  = CachedClubService(service, refresh_interval_seconds=60)
    await cached.start()        # initial fetch + starts background loop
    ...
    await cached.stop()         # cancels background loop
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.generated.models import Club, Court, TimeSlot

logger = logging.getLogger(__name__)

# How many days ahead to pre-fetch in each refresh cycle.
_DEFAULT_FETCH_DAYS = 8


class SlotCache:
    """
    Thread-safe in-memory store for courts and time slots.

    All data is replaced atomically on each refresh so readers never
    see a partially-updated state.
    """

    def __init__(self) -> None:
        self._courts: list[Court] = []
        self._slots: list[TimeSlot] = []
        self._last_refresh: datetime | None = None

    # ── Write ──────────────────────────────────────────────────────────

    def update(self, courts: list[Court], slots: list[TimeSlot]) -> None:
        """Atomically replace the cached data."""
        self._courts = list(courts)
        self._slots = list(slots)
        self._last_refresh = datetime.now(timezone.utc)
        logger.info(
            "Cache updated: %d courts, %d time slots (at %s)",
            len(self._courts),
            len(self._slots),
            self._last_refresh.isoformat(),
        )

    # ── Read ───────────────────────────────────────────────────────────

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
        slots = self._slots

        # Date range filter
        slots = [s for s in slots if date_from <= s.start_time.date() <= date_to]

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


class CachedClubService:
    """
    Cache-through wrapper that implements the TennisClubService protocol.

    On start, performs an initial data fetch then spawns a background
    asyncio task that re-fetches every *refresh_interval_seconds*.
    All reads are served from the in-memory cache.

    If the cache is empty (cold start / not yet populated), reads fall
    through to the underlying service directly.
    """

    def __init__(
        self,
        delegate: object,  # anything satisfying TennisClubService protocol
        *,
        refresh_interval_seconds: float = 60.0,
        fetch_days: int = _DEFAULT_FETCH_DAYS,
    ) -> None:
        self._delegate = delegate
        self._cache = SlotCache()
        self._refresh_interval = refresh_interval_seconds
        self._fetch_days = fetch_days
        self._task: asyncio.Task[None] | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Perform the initial cache fill and start the background loop."""
        await self._refresh()
        self._task = asyncio.create_task(self._refresh_loop(), name="cache-refresh")
        logger.info(
            "Background cache refresh started (every %ds)",
            self._refresh_interval,
        )

    async def stop(self) -> None:
        """Cancel the background refresh loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Background cache refresh stopped")

    # ── Background refresh ─────────────────────────────────────────────

    async def _refresh_loop(self) -> None:
        """Runs forever, refreshing the cache on a fixed interval."""
        while True:
            await asyncio.sleep(self._refresh_interval)
            try:
                await self._refresh()
            except Exception:
                logger.exception("Cache refresh failed – will retry next cycle")

    async def _refresh(self) -> None:
        """Fetch all courts + time slots from the delegate and update the cache."""
        logger.info("Refreshing cache from upstream...")
        today = date.today()
        date_to = today + timedelta(days=self._fetch_days - 1)

        courts = await self._delegate.list_courts()
        slots = await self._delegate.list_time_slots(
            date_from=today,
            date_to=date_to,
        )
        self._cache.update(courts, slots)

    # ── TennisClubService protocol ─────────────────────────────────────

    def get_club(self) -> Club:
        return self._delegate.get_club()

    async def list_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]:
        if not self._cache.is_populated:
            return await self._delegate.list_courts(
                surface_type=surface_type, court_type=court_type,
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

    # ── Introspection ──────────────────────────────────────────────────

    @property
    def last_refresh(self) -> datetime | None:
        return self._cache.last_refresh
