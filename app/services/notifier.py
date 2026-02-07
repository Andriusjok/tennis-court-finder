"""
Notification engine — detects slot status changes and sends alerts.

Runs as a background asyncio task alongside the cache refresh.
On each tick it:

1.  Snapshots the current slot statuses from the cache.
2.  Compares with the previous snapshot to find transitions
    (e.g. booked → free).
3.  Matches transitions against all active subscriptions.
4.  Sends one digest email per user with all matching slots.
5.  Logs each notification to the database.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime, time, timezone
from uuid import UUID

from app import db
from app.config import NOTIFIER_COOLDOWN, NOTIFIER_INTERVAL
from app.generated.models import NotificationSubscription, TimeSlot
from app.services.email import send_notification_email
from app.services.registry import registry

logger = logging.getLogger(__name__)

# slot_id → status  (the "previous" state for diffing)
_SlotSnapshot = dict[UUID, str]


class SlotNotifier:
    """
    Monitors cached time slots for status transitions and notifies
    users whose subscriptions match.
    """

    def __init__(self) -> None:
        self._prev_snapshot: _SlotSnapshot = {}
        self._task: asyncio.Task[None] | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Take the initial snapshot and start the background loop."""
        self._prev_snapshot = self._take_snapshot()
        logger.info(
            "Notifier started — tracking %d slots", len(self._prev_snapshot)
        )
        self._task = asyncio.create_task(
            self._loop(), name="slot-notifier"
        )

    async def stop(self) -> None:
        """Cancel the background loop."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Notifier stopped")

    # ── Background loop ───────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(NOTIFIER_INTERVAL)
            try:
                await self._tick()
            except Exception:
                logger.exception("Notifier tick failed — will retry")

    async def _tick(self) -> None:
        """One notification cycle."""
        current = self._take_snapshot()
        transitions = self._diff(self._prev_snapshot, current)
        self._prev_snapshot = current

        if not transitions:
            return

        logger.info("Detected %d slot status transitions", len(transitions))

        # Load all active subscriptions
        active_subs = await db.list_active_subscriptions()
        if not active_subs:
            return

        # Build a lookup: slot_id → TimeSlot (for the transitioned ones)
        slot_lookup = self._build_slot_lookup(transitions)

        # Group matched slots by (user_email, subscription)
        matches: dict[str, list[tuple[NotificationSubscription, list[TimeSlot]]]] = (
            defaultdict(list)
        )

        now = datetime.now(timezone.utc)

        for user_email, sub in active_subs:
            # Cooldown check
            if sub.last_notified_at:
                last = datetime.fromisoformat(str(sub.last_notified_at))
                if (now - last).total_seconds() < NOTIFIER_COOLDOWN:
                    continue

            matched_slots = self._match_subscription(sub, transitions, slot_lookup)
            if matched_slots:
                matches[user_email].append((sub, matched_slots))

        # Send digest emails
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

                # Log each matched slot
                for slot in slots:
                    await db.create_log(
                        subscription_id=str(sub.id),
                        time_slot=slot,
                        status=status,
                        error_message=error,
                    )

                # Bump the match counter
                await db.bump_match_count(str(sub.id))

                logger.info(
                    "Notified %s for subscription %s (%d slots, status=%s)",
                    user_email, sub.id, len(slots), status,
                )

    # ── Snapshot & diffing ─────────────────────────────────────────────

    def _take_snapshot(self) -> _SlotSnapshot:
        """Build a snapshot of all slot statuses currently in the cache."""
        snapshot: _SlotSnapshot = {}
        for svc in registry._services.values():
            if not svc._cache.is_populated:
                continue
            today = date.today()
            slots = svc._cache.get_time_slots(
                date_from=today,
                date_to=date(2099, 12, 31),  # all cached
            )
            for slot in slots:
                snapshot[slot.id] = slot.status
        return snapshot

    @staticmethod
    def _diff(
        prev: _SlotSnapshot, current: _SlotSnapshot
    ) -> dict[UUID, tuple[str, str]]:
        """
        Return slot IDs whose status changed.

        Returns {slot_id: (old_status, new_status)} for transitions only.
        New slots (not in prev) are treated as transitions from "unknown".
        """
        transitions: dict[UUID, tuple[str, str]] = {}
        for slot_id, new_status in current.items():
            old_status = prev.get(slot_id)
            if old_status is None:
                # First time seeing this slot — don't fire on initial load
                continue
            if old_status != new_status:
                transitions[slot_id] = (old_status, new_status)
        return transitions

    def _build_slot_lookup(
        self, transitions: dict[UUID, tuple[str, str]]
    ) -> dict[UUID, TimeSlot]:
        """Fetch the full TimeSlot objects for transitioned slot IDs."""
        lookup: dict[UUID, TimeSlot] = {}
        for svc in registry._services.values():
            if not svc._cache.is_populated:
                continue
            today = date.today()
            all_slots = svc._cache.get_time_slots(
                date_from=today,
                date_to=date(2099, 12, 31),
            )
            for slot in all_slots:
                if slot.id in transitions:
                    lookup[slot.id] = slot
        return lookup

    # ── Subscription matching ──────────────────────────────────────────

    @staticmethod
    def _match_subscription(
        sub: NotificationSubscription,
        transitions: dict[UUID, tuple[str, str]],
        slot_lookup: dict[UUID, TimeSlot],
    ) -> list[TimeSlot]:
        """
        Return the list of transitioned TimeSlots that match a subscription.
        """
        matched: list[TimeSlot] = []

        for slot_id, (old_status, new_status) in transitions.items():
            # 1. New status must be one the user watches for
            if new_status not in sub.notify_on_statuses:
                continue

            slot = slot_lookup.get(slot_id)
            if slot is None:
                continue

            # 2. Club must match
            if slot.club_id != sub.club_id:
                continue

            # 3. Court filter
            if sub.court_ids and slot.court_id not in [
                UUID(str(cid)) for cid in sub.court_ids
            ]:
                continue

            # 4. Surface filter
            if sub.surface_types and slot.surface_type not in sub.surface_types:
                continue

            # 5. Court type filter
            if sub.court_types and slot.court_type not in sub.court_types:
                continue

            # 6. Time-of-day filter
            slot_time = slot.start_time.strftime("%H:%M")
            if sub.time_from and slot_time < sub.time_from:
                continue
            if sub.time_to and slot_time > sub.time_to:
                continue

            # 7. Date matching
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


# ── Module-level singleton ────────────────────────────────────────────────
notifier = SlotNotifier()
