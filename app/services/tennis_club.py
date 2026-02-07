"""
Abstract interface for tennis club booking system integrations.

Every new club integration implements this protocol so the rest of the
application (routers, notification engine) is decoupled from the
underlying booking system.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.generated.models import Club, Court, TimeSlot


class TennisClubService(Protocol):
    """Protocol that every club integration must satisfy."""

    # ── Club metadata ─────────────────────────────────────────────────
    def get_club(self) -> Club:
        """Return the club's static metadata."""
        ...

    # ── Courts ────────────────────────────────────────────────────────
    async def list_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]:
        """Return courts, optionally filtered."""
        ...

    async def get_court(self, court_id: str) -> Court | None:
        """Return a single court by its ID, or None if not found."""
        ...

    # ── Time slots ────────────────────────────────────────────────────
    async def list_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]:
        """
        Return availability time slots for the given date range.
        Supports filtering by court, status, surface, and court type.
        """
        ...
