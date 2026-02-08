from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from app.services.teniso_erdve.config import (
    CALENDAR_URL,
    DEFAULT_HEADERS,
    PLACE_CLOSED,
    PLACE_OPEN,
)

logger = logging.getLogger(__name__)


@dataclass
class ParsedSlot:
    court_id: int
    court_name: str
    time: str  # "HH:MM"
    status: str  # "free", "booked"
    price: float | None = None


@dataclass
class ParsedSchedule:
    place: str  # "closed" or "open"
    courts: list[tuple[int, str]] = field(default_factory=list)
    slots: list[ParsedSlot] = field(default_factory=list)


class TenisoErdveClient:
    """HTTP client for Teniso Erdvė reservation calendar.

    Fetches court schedules from the AJAX endpoint that powers the
    reservation calendar at https://www.tenisoerdve.lt/rezervacijos.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_schedule(
        self,
        target_date: date,
        place: str = PLACE_CLOSED,
    ) -> ParsedSchedule:
        """Fetch the schedule for a given date and place type.

        Args:
            target_date: The date to fetch the schedule for.
            place: ``"closed"`` for indoor courts, ``"open"`` for outdoor.
        """
        params = {
            "activeday": target_date.isoformat(),
            "location": "frontend",
            "place": place,
            "UserID": "2",
        }
        logger.debug("Fetching Teniso Erdvė schedule: %s %s", CALENDAR_URL, params)
        resp = await self._client.get(CALENDAR_URL, params=params)
        resp.raise_for_status()
        return self._parse_html(resp.text, place)

    async def fetch_all_schedules(
        self,
        target_date: date,
    ) -> list[ParsedSchedule]:
        """Fetch schedules for both indoor and outdoor courts."""
        schedules: list[ParsedSchedule] = []
        for place in (PLACE_CLOSED, PLACE_OPEN):
            schedule = await self.fetch_schedule(target_date, place)
            if schedule.courts:
                schedules.append(schedule)
        return schedules

    # ------------------------------------------------------------------
    # HTML parsing
    # ------------------------------------------------------------------

    def _parse_html(self, html: str, place: str) -> ParsedSchedule:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table")
        if table is None:
            logger.warning("No table found in Teniso Erdvė HTML")
            return ParsedSchedule(place=place)

        schedule = ParsedSchedule(place=place)
        self._parse_table(table, schedule)
        return schedule

    def _parse_table(self, table: Tag, schedule: ParsedSchedule) -> None:
        rows = table.select("tr")
        if not rows:
            return

        # First row contains court names in <td class="fieldName"> cells
        header_row = rows[0]
        court_names: list[str] = []
        for cell in header_row.select("td.fieldName"):
            court_names.append(cell.get_text(strip=True))

        if not court_names:
            return

        # Parse data rows
        for row in rows[1:]:
            cells = row.select("td")
            if not cells:
                continue

            # First cell is the time label
            time_cell = cells[0]
            if "time" not in (time_cell.get("class") or []):
                continue

            time_text = time_cell.get_text(strip=True)
            # Time format is "HH:MM - HH:MM", we need the start time
            time_start = time_text.split("-")[0].strip()

            # Remaining cells correspond to courts (by position)
            slot_cells = cells[1:]
            for idx, cell in enumerate(slot_cells):
                if idx >= len(court_names):
                    break

                court_name = court_names[idx]
                status, court_id, price = self._parse_slot_cell(cell, idx)

                if status is None:
                    # "----" = not available, skip
                    continue

                # Register court if not yet seen
                if not any(cid == court_id for cid, _ in schedule.courts):
                    schedule.courts.append((court_id, court_name))

                schedule.slots.append(
                    ParsedSlot(
                        court_id=court_id,
                        court_name=court_name,
                        time=time_start,
                        status=status,
                        price=price,
                    )
                )

    @staticmethod
    def _parse_slot_cell(
        cell: Tag, position_idx: int
    ) -> tuple[str | None, int, float | None]:
        """Parse a single slot cell.

        Returns:
            Tuple of (status, court_id, price).
            status is None if the slot is unavailable ("----").
        """
        classes = cell.get("class") or []

        # Free slot: class="notSelected" with data attributes
        if "notSelected" in classes:
            kort = cell.get("data-kort")
            court_id = int(kort) if kort else position_idx + 1
            price_str = cell.get("data-price")
            price = float(price_str) if price_str else None
            return "free", court_id, price

        # Reserved slot: class="reserved"
        if "reserved" in classes:
            # Reserved cells don't have data-kort, use position index
            # The court ID mapping is: position 0 -> kort 1, etc.
            court_id = position_idx + 1
            return "booked", court_id, None

        # Unavailable slot: just "----" text
        text = cell.get_text(strip=True)
        if text == "----" or not text:
            return None, position_idx + 1, None

        # Unknown state - treat as unavailable
        logger.debug("Unknown cell state: classes=%s text=%s", classes, text)
        return None, position_idx + 1, None
