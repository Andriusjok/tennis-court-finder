"""
Mock implementation of TennisClubService for unit tests.

Does not make any HTTP calls – returns canned data from tests.mocks.models.
"""

from __future__ import annotations

from datetime import date

from app.generated.models import Club, Court, TimeSlot
from tests.mocks.models import MOCK_CLUB, MOCK_COURTS, MOCK_TIME_SLOTS


class MockClubService:
    """
    In-memory implementation of TennisClubService that returns mock data.

    Pass custom clubs / courts / slots to override the defaults.
    """

    def __init__(
        self,
        club: Club | None = None,
        courts: list[Court] | None = None,
        time_slots: list[TimeSlot] | None = None,
    ) -> None:
        self._club = club or MOCK_CLUB
        self._courts = courts if courts is not None else list(MOCK_COURTS)
        self._time_slots = time_slots if time_slots is not None else list(MOCK_TIME_SLOTS)

    # ── Club metadata ──────────────────────────────────────────────────

    def get_club(self) -> Club:
        return self._club

    # ── Courts ─────────────────────────────────────────────────────────

    async def list_courts(
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

    async def get_court(self, court_id: str) -> Court | None:
        for court in self._courts:
            if str(court.id) == court_id:
                return court
        return None

    # ── Lifecycle (no-op for tests) ───────────────────────────────────

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    # ── Time slots ─────────────────────────────────────────────────────

    async def list_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]:
        slots = self._time_slots

        if court_id:
            slots = [s for s in slots if str(s.court_id) == court_id]
        if status:
            slots = [s for s in slots if s.status == status]
        if surface_type:
            slots = [s for s in slots if s.surface_type == surface_type]
        if court_type:
            slots = [s for s in slots if s.court_type == court_type]

        # Filter by date range
        slots = [
            s
            for s in slots
            if date_from <= s.start_time.date() <= date_to
        ]

        slots.sort(key=lambda s: (s.start_time, s.court_name))
        return slots
