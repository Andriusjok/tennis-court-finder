from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid5

from app.generated.models import Club, Court, TimeSlot
from app.services.baltic_tennis.client import BalticTennisClient
from app.services.baltic_tennis.config import (
    CLUB_ADDRESS,
    CLUB_CITY,
    CLUB_ID,
    CLUB_NAME,
    CLUB_PHONE,
    CLUB_UUID_NS,
    CLUB_WEBSITE,
    DEFAULT_COURT_TYPE,
    DEFAULT_SURFACE_TYPE,
    SLOT_DURATION_MINUTES,
    TENNIS_PLACE_ID,
)

logger = logging.getLogger(__name__)

_COURT_UUID_NS = CLUB_UUID_NS


def _court_uuid(court_id: int) -> UUID:
    return uuid5(_COURT_UUID_NS, f"bt-court-{court_id}")


def _slot_uuid(court_id: int, date_str: str, time_from: str) -> UUID:
    return uuid5(_COURT_UUID_NS, f"bt-slot-{court_id}-{date_str}-{time_from}")


class BalticTennisService:
    def __init__(self, client: BalticTennisClient) -> None:
        self._client = client
        self._courts_cache: list[Court] | None = None

    def get_club(self) -> Club:
        return Club(
            id=CLUB_ID,
            name=CLUB_NAME,
            address=CLUB_ADDRESS,
            city=CLUB_CITY,
            phone=CLUB_PHONE,
            website=CLUB_WEBSITE,
            image_url=None,
            courts_count=None,
        )

    async def list_courts(
        self,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[Court]:
        courts = await self._ensure_courts()
        if surface_type and surface_type != DEFAULT_SURFACE_TYPE:
            return []
        if court_type and court_type != DEFAULT_COURT_TYPE:
            return []
        return courts

    async def get_court(self, court_id: str) -> Court | None:
        courts = await self._ensure_courts()
        target = UUID(court_id) if isinstance(court_id, str) else court_id
        for court in courts:
            if court.id == target:
                return court
        return None

    async def _ensure_courts(self) -> list[Court]:
        if self._courts_cache is not None:
            return self._courts_cache

        today = date.today()
        schedule = await self._client.fetch_schedule(today, TENNIS_PLACE_ID)

        courts: list[Court] = []
        for court_id, court_name in schedule.courts:
            courts.append(
                Court(
                    id=_court_uuid(court_id),
                    club_id=CLUB_ID,
                    name=court_name,
                    surface_type=DEFAULT_SURFACE_TYPE,
                    court_type=DEFAULT_COURT_TYPE,
                    description=None,
                )
            )

        self._courts_cache = courts
        logger.info("Cached %d courts for Baltic Tennis", len(courts))
        return courts

    async def list_time_slots(
        self,
        date_from: date,
        date_to: date,
        court_id: str | None = None,
        status: str | None = None,
        surface_type: str | None = None,
        court_type: str | None = None,
    ) -> list[TimeSlot]:
        if surface_type and surface_type != DEFAULT_SURFACE_TYPE:
            return []
        if court_type and court_type != DEFAULT_COURT_TYPE:
            return []

        target_court_uuid: UUID | None = None
        if court_id:
            target_court_uuid = UUID(court_id) if isinstance(court_id, str) else court_id

        dates: list[date] = []
        d = date_from
        while d <= date_to:
            dates.append(d)
            d += timedelta(days=1)

        if not dates:
            return []

        slots: list[TimeSlot] = []
        for target_date in dates:
            schedule = await self._client.fetch_schedule(target_date, TENNIS_PLACE_ID)

            if self._courts_cache is None and schedule.courts:
                self._courts_cache = [
                    Court(
                        id=_court_uuid(cid),
                        club_id=CLUB_ID,
                        name=cname,
                        surface_type=DEFAULT_SURFACE_TYPE,
                        court_type=DEFAULT_COURT_TYPE,
                        description=None,
                    )
                    for cid, cname in schedule.courts
                ]

            date_str = target_date.isoformat()
            for parsed_slot in schedule.slots:
                c_uuid = _court_uuid(parsed_slot.court_id)

                if target_court_uuid and c_uuid != target_court_uuid:
                    continue
                if status and parsed_slot.status != status:
                    continue

                start_dt = datetime.strptime(
                    f"{date_str} {parsed_slot.time}",
                    "%Y-%m-%d %H:%M",
                ).replace(tzinfo=UTC)
                end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MINUTES)

                slots.append(
                    TimeSlot(
                        id=_slot_uuid(parsed_slot.court_id, date_str, parsed_slot.time),
                        court_id=c_uuid,
                        club_id=CLUB_ID,
                        court_name=parsed_slot.court_name,
                        surface_type=DEFAULT_SURFACE_TYPE,
                        court_type=DEFAULT_COURT_TYPE,
                        start_time=start_dt,
                        end_time=end_dt,
                        duration_minutes=SLOT_DURATION_MINUTES,
                        status=parsed_slot.status,
                        price=schedule.price_eur,
                        currency="EUR" if schedule.price_eur else None,
                    )
                )

        slots.sort(key=lambda s: (s.start_time, s.court_name))
        return slots
