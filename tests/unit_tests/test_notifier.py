"""Tests for the SlotNotifier matching logic."""

from datetime import datetime, timezone
from uuid import UUID

from app.generated.models import NotificationSubscription, TimeSlot
from app.services.notifier import SlotNotifier
from tests.mocks.models import (
    MOCK_COURT_HARD_INDOOR,
    MOCK_SLOT_FREE,
    _uuid,
)


def _make_subscription(**overrides) -> NotificationSubscription:
    """Factory for test subscriptions."""
    defaults = dict(
        id=_uuid("sub-test"),
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
        active=True,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return NotificationSubscription(**defaults)


def _make_time_slot(**overrides) -> TimeSlot:
    """Factory for test time slots."""
    defaults = dict(
        id=_uuid("slot-test"),
        court_id=MOCK_COURT_HARD_INDOOR.id,
        club_id="test-club",
        court_name="Court 1",
        surface_type="hard",
        court_type="indoor",
        start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),  # Tuesday
        end_time=datetime(2026, 2, 10, 19, 0, tzinfo=timezone.utc),
        duration_minutes=60,
        status="free",
        price=25.0,
        currency="EUR",
    )
    defaults.update(overrides)
    return TimeSlot(**defaults)


class TestDiff:
    """Test the snapshot diffing logic."""

    def test_no_changes(self):
        prev = {_uuid("s1"): "booked", _uuid("s2"): "free"}
        curr = {_uuid("s1"): "booked", _uuid("s2"): "free"}
        assert SlotNotifier._diff(prev, curr) == {}

    def test_status_change_detected(self):
        prev = {_uuid("s1"): "booked"}
        curr = {_uuid("s1"): "free"}
        result = SlotNotifier._diff(prev, curr)
        assert result == {_uuid("s1"): ("booked", "free")}

    def test_new_slot_ignored(self):
        """New slots (not in prev) should NOT fire — avoids noise on startup."""
        prev = {}
        curr = {_uuid("s1"): "free"}
        assert SlotNotifier._diff(prev, curr) == {}

    def test_removed_slot_ignored(self):
        prev = {_uuid("s1"): "free"}
        curr = {}
        assert SlotNotifier._diff(prev, curr) == {}

    def test_multiple_changes(self):
        prev = {_uuid("s1"): "booked", _uuid("s2"): "free", _uuid("s3"): "booked"}
        curr = {_uuid("s1"): "free", _uuid("s2"): "free", _uuid("s3"): "for_sale"}
        result = SlotNotifier._diff(prev, curr)
        assert len(result) == 2
        assert result[_uuid("s1")] == ("booked", "free")
        assert result[_uuid("s3")] == ("booked", "for_sale")


class TestMatchSubscription:
    """Test subscription matching against slot transitions."""

    def test_basic_match(self):
        sub = _make_subscription(notify_on_statuses=["free"])
        slot = _make_time_slot()
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert len(matched) == 1
        assert matched[0].id == slot.id

    def test_wrong_status_no_match(self):
        sub = _make_subscription(notify_on_statuses=["for_sale"])
        slot = _make_time_slot(status="free")
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_wrong_club_no_match(self):
        sub = _make_subscription(club_id="other-club")
        slot = _make_time_slot(club_id="test-club")
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_court_filter(self):
        other_court_id = _uuid("court-other")
        sub = _make_subscription(court_ids=[other_court_id])
        slot = _make_time_slot(court_id=MOCK_COURT_HARD_INDOOR.id)
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_surface_filter(self):
        sub = _make_subscription(surface_types=["clay"])
        slot = _make_time_slot(surface_type="hard")
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_court_type_filter(self):
        sub = _make_subscription(court_types=["outdoor"])
        slot = _make_time_slot(court_type="indoor")
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_time_range_filter(self):
        sub = _make_subscription(time_from="19:00", time_to="21:00")
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_time_range_match(self):
        sub = _make_subscription(time_from="17:00", time_to="19:00")
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert len(matched) == 1

    def test_recurring_day_filter(self):
        sub = _make_subscription(
            is_recurring=True,
            days_of_week=["wednesday"],  # slot is on Tuesday
        )
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),  # Tuesday
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_recurring_day_match(self):
        sub = _make_subscription(
            is_recurring=True,
            days_of_week=["tuesday"],
        )
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),  # Tuesday
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert len(matched) == 1

    def test_specific_dates_no_match(self):
        sub = _make_subscription(
            specific_dates=["2026-02-11"],  # Wednesday
        )
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),  # Tuesday
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_date_range_filter(self):
        from datetime import date

        sub = _make_subscription(
            date_range_start=date(2026, 2, 15),
            date_range_end=date(2026, 2, 28),
        )
        slot = _make_time_slot(
            start_time=datetime(2026, 2, 10, 18, 0, tzinfo=timezone.utc),  # Before range
        )
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert matched == []

    def test_inactive_sub_filtered_at_caller_level(self):
        """Inactive subs are filtered by the caller, not _match_subscription."""
        sub = _make_subscription(active=False)
        slot = _make_time_slot()
        transitions = {slot.id: ("booked", "free")}
        lookup = {slot.id: slot}

        # _match_subscription doesn't check active — the caller does
        matched = SlotNotifier._match_subscription(sub, transitions, lookup)
        assert len(matched) == 1  # Still matches at this level
