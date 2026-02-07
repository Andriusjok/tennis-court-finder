from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid5

from app.generated.models import Club, Court, TimeSlot
from app.services.seb_arena.client import SebArenaClient
from app.services.seb_arena.config import (
    CLUB_ADDRESS,
    CLUB_CITY,
    CLUB_ID,
    CLUB_NAME,
    CLUB_PHONE,
    CLUB_UUID_NS,
    CLUB_WEBSITE,
    PLACE_MAPPINGS,
    STATUS_MAP,
    TENNIS_PLACE_IDS,
)

logger = logging.getLogger(__name__)

_COURT_UUID_NS = CLUB_UUID_NS


def _court_uuid(court_id: int) -> UUID:
    return uuid5(_COURT_UUID_NS, f"court-{court_id}")


def _slot_uuid(court_id: int, date_str: str, time_from: str) -> UUID:
    return uuid5(_COURT_UUID_NS, f"slot-{court_id}-{date_str}-{time_from}")


class SebArenaService:
    def __init__(self, client: SebArenaClient) -> None:
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
        if surface_type:
            courts = [c for c in courts if c.surface_type == surface_type]
        if court_type:
            courts = [c for c in courts if c.court_type == court_type]
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
        batch = await self._client.get_place_info_batch(
            dates=[today],
            place_ids=TENNIS_PLACE_IDS,
            include_court_name=True,
        )

        courts: list[Court] = []
        for place_data in batch.data:
            mapping = PLACE_MAPPINGS.get(place_data.place)
            if mapping is None:
                continue
            for court_list in place_data.data:
                for court_entry in court_list:
                    court = Court(
                        id=_court_uuid(court_entry.courtID),
                        club_id=CLUB_ID,
                        name=court_entry.courtName or f"Court {court_entry.courtID}",
                        surface_type=mapping.surface_type,
                        court_type=mapping.court_type,
                        description=None,
                    )
                    if not any(c.id == court.id for c in courts):
                        courts.append(court)

        self._courts_cache = courts
        logger.info("Cached %d courts for SEB Arena", len(courts))
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
        dates: list[date] = []
        d = date_from
        while d <= date_to:
            dates.append(d)
            d += timedelta(days=1)

        if not dates:
            return []

        courts = await self._ensure_courts()
        court_map = {c.id: c for c in courts}

        batch = await self._client.get_place_info_batch(
            dates=dates,
            place_ids=TENNIS_PLACE_IDS,
            include_court_name=True,
        )

        slots: list[TimeSlot] = []
        for place_data in batch.data:
            mapping = PLACE_MAPPINGS.get(place_data.place)
            if mapping is None:
                continue

            if surface_type and mapping.surface_type != surface_type:
                continue
            if court_type and mapping.court_type != court_type:
                continue

            for court_list in place_data.data:
                for court_entry in court_list:
                    c_uuid = _court_uuid(court_entry.courtID)

                    if court_id:
                        target_uuid = UUID(court_id) if isinstance(court_id, str) else court_id
                        if c_uuid != target_uuid:
                            continue

                    court_info = court_map.get(c_uuid)
                    court_name = (
                        court_info.name
                        if court_info
                        else court_entry.courtName or f"Court {court_entry.courtID}"
                    )

                    for _time_key, slot_entry in court_entry.timetable.items():
                        mapped_status = STATUS_MAP.get(slot_entry.status)
                        if mapped_status is None:
                            continue

                        if status and mapped_status != status:
                            continue

                        slot_date = court_entry.date
                        start_dt = datetime.strptime(
                            f"{slot_date} {slot_entry.from_}",
                            "%Y-%m-%d %H:%M:%S",
                        ).replace(tzinfo=UTC)
                        end_dt = datetime.strptime(
                            f"{slot_date} {slot_entry.to}",
                            "%Y-%m-%d %H:%M:%S",
                        ).replace(tzinfo=UTC)

                        duration = int((end_dt - start_dt).total_seconds() / 60)

                        slots.append(
                            TimeSlot(
                                id=_slot_uuid(court_entry.courtID, slot_date, slot_entry.from_),
                                court_id=c_uuid,
                                club_id=CLUB_ID,
                                court_name=court_name,
                                surface_type=mapping.surface_type,
                                court_type=mapping.court_type,
                                start_time=start_dt,
                                end_time=end_dt,
                                duration_minutes=duration,
                                status=mapped_status,
                                price=None,
                                currency=None,
                            )
                        )

        slots.sort(key=lambda s: (s.start_time, s.court_name))
        return slots
