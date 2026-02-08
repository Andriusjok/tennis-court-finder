from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from app.services.baltic_tennis.config import (
    BASE_URL,
    DEFAULT_HEADERS,
    RESERVATION_URL,
    TENNIS_PLACE_ID,
)

logger = logging.getLogger(__name__)

_LOGIN_URL = f"{BASE_URL}/user/login"
_ANON_CREDENTIALS = {
    "LoginForm[var_login]": "BalticTennis",
    "LoginForm[var_password]": "6B+WPkdX,`d#]a:",
}


@dataclass
class ParsedSlot:
    court_id: int
    court_name: str
    time: str  # "HH:MM"
    status: str  # "free", "booked", "for_sale"


@dataclass
class ParsedSchedule:
    courts: list[tuple[int, str]] = field(default_factory=list)
    slots: list[ParsedSlot] = field(default_factory=list)
    price_eur: float | None = None


class BalticTennisClient:
    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        )
        self._authenticated = False

    async def close(self) -> None:
        await self._client.aclose()

    async def _ensure_session(self) -> None:
        if self._authenticated:
            return
        logger.debug("Establishing anonymous session with Baltic Tennis")
        await self._client.get(_LOGIN_URL)
        resp = await self._client.post(_LOGIN_URL, data=_ANON_CREDENTIALS)
        if "reservation" in str(resp.url):
            self._authenticated = True
            logger.info("Baltic Tennis anonymous session established")
        else:
            logger.warning("Baltic Tennis anonymous login may have failed (url=%s)", resp.url)

    async def fetch_schedule(
        self,
        target_date: date,
        place_id: int = TENNIS_PLACE_ID,
    ) -> ParsedSchedule:
        await self._ensure_session()
        url = RESERVATION_URL
        params = {
            "sDate": f"{target_date.year}-{target_date.month}-{target_date.day:02d}",
            "iPlaceId": str(place_id),
        }
        logger.debug("Fetching Baltic Tennis schedule: %s %s", url, params)
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()

        schedule = self._parse_html(resp.text)
        if not schedule.courts and "login" in str(resp.url).lower():
            logger.warning("Session expired, re-authenticating...")
            self._authenticated = False
            await self._ensure_session()
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            schedule = self._parse_html(resp.text)

        return schedule

    def _parse_html(self, html: str) -> ParsedSchedule:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.rbt-table")
        if table is None:
            logger.warning("No .rbt-table found in Baltic Tennis HTML")
            return ParsedSchedule()

        schedule = ParsedSchedule()
        self._parse_price(soup, schedule)
        self._parse_table(table, schedule)
        return schedule

    def _parse_price(self, soup: BeautifulSoup, schedule: ParsedSchedule) -> None:
        legend = soup.select_one(".booking-table-legend")
        if legend is None:
            return
        for item in legend.select(".legend-item"):
            text = item.get_text(strip=True)
            if "€" in text:
                try:
                    price_str = text.replace("€", "").strip().split()[-1]
                    schedule.price_eur = float(price_str)
                except (ValueError, IndexError):
                    pass

    def _parse_table(self, table: Tag, schedule: ParsedSchedule) -> None:
        tbody = table.select_one("tbody")
        if tbody is None:
            return

        seen_courts: set[int] = set()

        for row in tbody.select("tr"):
            court_cell = row.select_one("td.rbt-sticky-col span")
            if court_cell is None:
                continue
            court_name = court_cell.get_text(strip=True)

            slot_cells = row.select("td:not(.rbt-sticky-col)")
            for cell in slot_cells:
                link = cell.select_one("a[data-court][data-time]")
                if link is None:
                    continue

                court_id = int(link["data-court"])
                time_str = link["data-time"]

                if court_id not in seen_courts:
                    seen_courts.add(court_id)
                    schedule.courts.append((court_id, court_name))

                status = self._cell_status(cell, link)
                schedule.slots.append(
                    ParsedSlot(
                        court_id=court_id,
                        court_name=court_name,
                        time=time_str,
                        status=status,
                    )
                )

    @staticmethod
    def _cell_status(cell: Tag, link: Tag) -> str:
        classes = " ".join(cell.get("class", []))
        perparduodamas = (link.get("data-perparduodamas") or "").strip()
        if perparduodamas:
            return "for_sale"
        if "booking-slot-na" in classes:
            return "booked"
        return "free"
