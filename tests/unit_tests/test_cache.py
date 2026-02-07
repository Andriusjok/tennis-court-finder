"""Tests for the caching layer."""

import asyncio
from datetime import date

import pytest

from app.services.cache import CachedClubService, SlotCache
from tests.mocks.models import (
    MOCK_CLUB,
    MOCK_COURT_CLAY_OUTDOOR,
    MOCK_COURT_HARD_INDOOR,
    MOCK_COURTS,
    MOCK_TIME_SLOTS,
)
from tests.mocks.services import MockClubService

# ── SlotCache tests ────────────────────────────────────────────────────────


class TestSlotCache:
    def test_empty_cache_is_not_populated(self):
        cache = SlotCache()
        assert cache.is_populated is False
        assert cache.last_refresh is None

    def test_update_populates_cache(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        assert cache.is_populated is True
        assert cache.last_refresh is not None

    def test_get_courts_all(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        assert len(cache.get_courts()) == len(MOCK_COURTS)

    def test_get_courts_filter_surface(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        courts = cache.get_courts(surface_type="clay")
        assert len(courts) == 1
        assert courts[0].surface_type == "clay"

    def test_get_courts_filter_court_type(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        courts = cache.get_courts(court_type="indoor")
        assert len(courts) == 2

    def test_get_court_by_id(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        court = cache.get_court(str(MOCK_COURT_HARD_INDOOR.id))
        assert court is not None
        assert court.name == "Court 1"

    def test_get_court_not_found(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        court = cache.get_court("00000000-0000-0000-0000-000000000099")
        assert court is None

    def test_get_time_slots_all_today(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        today = date.today()
        slots = cache.get_time_slots(date_from=today, date_to=today)
        assert len(slots) == len(MOCK_TIME_SLOTS)

    def test_get_time_slots_filter_status(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        today = date.today()
        slots = cache.get_time_slots(date_from=today, date_to=today, status="free")
        assert all(s.status == "free" for s in slots)

    def test_get_time_slots_filter_court_id(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        today = date.today()
        court_id = str(MOCK_COURT_CLAY_OUTDOOR.id)
        slots = cache.get_time_slots(date_from=today, date_to=today, court_id=court_id)
        assert all(str(s.court_id) == court_id for s in slots)

    def test_get_time_slots_filter_surface(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        today = date.today()
        slots = cache.get_time_slots(
            date_from=today,
            date_to=today,
            surface_type="clay",
        )
        assert all(s.surface_type == "clay" for s in slots)

    def test_get_time_slots_empty_date_range(self):
        cache = SlotCache()
        cache.update(MOCK_COURTS, MOCK_TIME_SLOTS)
        far_future = date(2030, 1, 1)
        slots = cache.get_time_slots(date_from=far_future, date_to=far_future)
        assert slots == []


# ── CachedClubService tests ───────────────────────────────────────────────


class TestCachedClubService:
    @pytest.fixture()
    def mock_delegate(self) -> MockClubService:
        return MockClubService(club=MOCK_CLUB)

    @pytest.fixture()
    def cached_service(self, mock_delegate: MockClubService) -> CachedClubService:
        return CachedClubService(
            mock_delegate,
            refresh_interval_seconds=60.0,
        )

    def test_get_club_delegates(self, cached_service: CachedClubService):
        club = cached_service.get_club()
        assert club.id == MOCK_CLUB.id

    @pytest.mark.asyncio
    async def test_list_courts_fallback_when_empty(
        self,
        cached_service: CachedClubService,
    ):
        """Before start(), cache is empty — should fall through to delegate."""
        courts = await cached_service.list_courts()
        assert len(courts) == len(MOCK_COURTS)

    @pytest.mark.asyncio
    async def test_start_populates_cache(self, cached_service: CachedClubService):
        await cached_service.start()
        try:
            assert cached_service.last_refresh is not None
            courts = await cached_service.list_courts()
            assert len(courts) == len(MOCK_COURTS)
        finally:
            await cached_service.stop()

    @pytest.mark.asyncio
    async def test_list_courts_from_cache(self, cached_service: CachedClubService):
        await cached_service.start()
        try:
            courts = await cached_service.list_courts(surface_type="clay")
            assert len(courts) == 1
            assert courts[0].surface_type == "clay"
        finally:
            await cached_service.stop()

    @pytest.mark.asyncio
    async def test_list_time_slots_from_cache(self, cached_service: CachedClubService):
        await cached_service.start()
        try:
            today = date.today()
            slots = await cached_service.list_time_slots(
                date_from=today,
                date_to=today,
                status="free",
            )
            assert len(slots) >= 1
            assert all(s.status == "free" for s in slots)
        finally:
            await cached_service.stop()

    @pytest.mark.asyncio
    async def test_get_court_from_cache(self, cached_service: CachedClubService):
        await cached_service.start()
        try:
            court = await cached_service.get_court(str(MOCK_COURT_HARD_INDOOR.id))
            assert court is not None
            assert court.name == "Court 1"
        finally:
            await cached_service.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_background_task(self, cached_service: CachedClubService):
        await cached_service.start()
        assert cached_service._task is not None
        assert not cached_service._task.done()

        await cached_service.stop()
        assert cached_service._task is None

    @pytest.mark.asyncio
    async def test_background_refresh_runs(self):
        """With a very short interval, the cache should refresh at least once."""
        delegate = MockClubService(club=MOCK_CLUB)
        cached = CachedClubService(
            delegate,
            refresh_interval_seconds=0.1,  # 100ms for testing
        )
        await cached.start()
        try:
            first_refresh = cached.last_refresh
            await asyncio.sleep(0.3)
            # After 300ms with 100ms interval, it should have refreshed
            assert cached.last_refresh is not None
            assert cached.last_refresh > first_refresh
        finally:
            await cached.stop()
