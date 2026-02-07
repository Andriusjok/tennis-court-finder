from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from app import db
from app.config import NOTIFIER_COOLDOWN, NOTIFIER_INTERVAL
from app.generated.models import NotificationSubscription, TimeSlot
from app.services.background import BackgroundWorker
from app.services.email import send_notification_email
from app.services.registry import registry

logger = logging.getLogger(__name__)

_SlotSnapshot = dict[UUID, str]

_FAR_FUTURE = date(2099, 12, 31)


class SlotNotifier(BackgroundWorker):
    def __init__(self) -> None:
        super().__init__(interval=NOTIFIER_INTERVAL, name="slot-notifier")
        self._prev_snapshot: _SlotSnapshot = {}

    async def _on_start(self) -> None:
        self._prev_snapshot = self._take_snapshot()
        logger.info("Notifier tracking %d slots", len(self._prev_snapshot))

    async def _tick(self) -> None:
        current = self._take_snapshot()
        transitions = self._diff(self._prev_snapshot, current)
        self._prev_snapshot = current

        if not transitions:
            return

        logger.info("Detected %d slot status transitions", len(transitions))

        active_subs = await db.list_active_subscriptions()
        if not active_subs:
            return

        slot_lookup = {
            slot.id: slot for slot in self._all_cached_slots() if slot.id in transitions
        }

        matches: dict[str, list[tuple[NotificationSubscription, list[TimeSlot]]]] = defaultdict(
            list
        )
        now = datetime.now(UTC)

        for user_email, sub in active_subs:
            if sub.last_notified_at:
                last = datetime.fromisoformat(str(sub.last_notified_at))
                if (now - last).total_seconds() < NOTIFIER_COOLDOWN:
                    continue

            matched_slots = self._match_subscription(sub, transitions, slot_lookup)
            if matched_slots:
                matches[user_email].append((sub, matched_slots))

        for user_email, sub_matches in matches.items():
            for sub, slots in sub_matches:
                club_name = sub.club_name or sub.club_id
                try:
                    await send_notification_email(user_email, club_name, slots)
                    status = "sent"
                    error = None
                except Exception as exc:
                    status = "failed"
                    error = str(exc)

                for slot in slots:
                    await db.create_log(
                        subscription_id=str(sub.id),
                        time_slot=slot,
                        status=status,
                        error_message=error,
                    )
                await db.bump_match_count(str(sub.id))
                logger.info(
                    "Notified %s for subscription %s (%d slots, status=%s)",
                    user_email,
                    sub.id,
                    len(slots),
                    status,
                )

    def _all_cached_slots(self) -> list[TimeSlot]:
        today = date.today()
        result: list[TimeSlot] = []
        for svc in registry._services.values():
            if svc._cache.is_populated:
                result.extend(svc._cache.get_time_slots(date_from=today, date_to=_FAR_FUTURE))
        return result

    def _take_snapshot(self) -> _SlotSnapshot:
        return {slot.id: slot.status for slot in self._all_cached_slots()}

    @staticmethod
    def _diff(prev: _SlotSnapshot, current: _SlotSnapshot) -> dict[UUID, tuple[str, str]]:
        transitions: dict[UUID, tuple[str, str]] = {}
        for slot_id, new_status in current.items():
            old_status = prev.get(slot_id)
            if old_status is not None and old_status != new_status:
                transitions[slot_id] = (old_status, new_status)
        return transitions

    @staticmethod
    def _match_subscription(
        sub: NotificationSubscription,
        transitions: dict[UUID, tuple[str, str]],
        slot_lookup: dict[UUID, TimeSlot],
    ) -> list[TimeSlot]:
        matched: list[TimeSlot] = []

        for slot_id, (_old_status, new_status) in transitions.items():
            if new_status not in sub.notify_on_statuses:
                continue

            slot = slot_lookup.get(slot_id)
            if slot is None:
                continue

            if slot.club_id != sub.club_id:
                continue

            if sub.court_ids and slot.court_id not in [UUID(str(cid)) for cid in sub.court_ids]:
                continue

            if sub.surface_types and slot.surface_type not in sub.surface_types:
                continue

            if sub.court_types and slot.court_type not in sub.court_types:
                continue

            slot_time = slot.start_time.strftime("%H:%M")
            if sub.time_from and slot_time < sub.time_from:
                continue
            if sub.time_to and slot_time > sub.time_to:
                continue

            slot_date = slot.start_time.date()
            slot_dow = slot_date.strftime("%A").lower()

            if sub.is_recurring and sub.days_of_week:
                if slot_dow not in sub.days_of_week:
                    continue
            elif sub.specific_dates:
                specific = [
                    d if isinstance(d, date) else date.fromisoformat(str(d))
                    for d in sub.specific_dates
                ]
                if slot_date not in specific:
                    continue

            if sub.date_range_start:
                dr_start = (
                    sub.date_range_start
                    if isinstance(sub.date_range_start, date)
                    else date.fromisoformat(str(sub.date_range_start))
                )
                if slot_date < dr_start:
                    continue
            if sub.date_range_end:
                dr_end = (
                    sub.date_range_end
                    if isinstance(sub.date_range_end, date)
                    else date.fromisoformat(str(sub.date_range_end))
                )
                if slot_date > dr_end:
                    continue

            matched.append(slot)

        return matched


notifier = SlotNotifier()
