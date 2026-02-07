"""
Pre-built model instances for use in tests.

Import individual fixtures or use the factory helpers to create
custom variants:

    from tests.mocks.models import MOCK_CLUB, make_court, make_time_slot
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid5, NAMESPACE_URL

from app.generated.models import (
    Club,
    Court,
    NotificationSubscription,
    NotificationSubscriptionCreate,
    TimeSlot,
    UserInfo,
)

# ── Deterministic UUIDs ────────────────────────────────────────────────────
# Namespace for generating stable test UUIDs
_TEST_NS = UUID("00000000-0000-0000-0000-000000000000")


def _uuid(name: str) -> UUID:
    return uuid5(_TEST_NS, name)


# ── Users ──────────────────────────────────────────────────────────────────

MOCK_USER = UserInfo(
    email="player@example.com",
    created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
)

MOCK_USER_2 = UserInfo(
    email="coach@example.com",
    created_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
)

# ── Club ───────────────────────────────────────────────────────────────────

MOCK_CLUB = Club(
    id="test-club",
    name="Test Tennis Club",
    address="123 Racket Lane",
    city="Vilnius",
    phone="+37060000000",
    website="https://test-tennis.lt",
    image_url=None,
    courts_count=3,
)

MOCK_CLUB_2 = Club(
    id="other-club",
    name="Other Tennis Club",
    address="456 Court Street",
    city="Kaunas",
    phone="+37060000001",
    website="https://other-tennis.lt",
    image_url=None,
    courts_count=2,
)

# ── Courts ─────────────────────────────────────────────────────────────────

MOCK_COURT_HARD_INDOOR = Court(
    id=_uuid("court-1"),
    club_id="test-club",
    name="Court 1",
    surface_type="hard",
    court_type="indoor",
    description="Main indoor hard court",
)

MOCK_COURT_CLAY_OUTDOOR = Court(
    id=_uuid("court-2"),
    club_id="test-club",
    name="Court 2",
    surface_type="clay",
    court_type="outdoor",
    description="Outdoor clay court",
)

MOCK_COURT_CARPET_INDOOR = Court(
    id=_uuid("court-3"),
    club_id="test-club",
    name="Court 3",
    surface_type="carpet",
    court_type="indoor",
    description=None,
)

MOCK_COURTS = [MOCK_COURT_HARD_INDOOR, MOCK_COURT_CLAY_OUTDOOR, MOCK_COURT_CARPET_INDOOR]

# ── Time slots ─────────────────────────────────────────────────────────────

_TODAY = date.today()
_BASE_DT = datetime(_TODAY.year, _TODAY.month, _TODAY.day, 10, 0, tzinfo=timezone.utc)


def make_time_slot(
    court: Court = MOCK_COURT_HARD_INDOOR,
    start_time: datetime | None = None,
    duration_minutes: int = 60,
    status: str = "free",
) -> TimeSlot:
    """Factory to create a TimeSlot with sensible defaults."""
    st = start_time or _BASE_DT
    return TimeSlot(
        id=_uuid(f"slot-{court.id}-{st.isoformat()}"),
        court_id=court.id,
        club_id=court.club_id,
        court_name=court.name,
        surface_type=court.surface_type,
        court_type=court.court_type,
        start_time=st,
        end_time=st + timedelta(minutes=duration_minutes),
        duration_minutes=duration_minutes,
        status=status,
        price=25.0,
        currency="EUR",
    )


MOCK_SLOT_FREE = make_time_slot(status="free")
MOCK_SLOT_BOOKED = make_time_slot(
    start_time=_BASE_DT + timedelta(hours=1),
    status="booked",
)
MOCK_SLOT_FOR_SALE = make_time_slot(
    start_time=_BASE_DT + timedelta(hours=2),
    status="for_sale",
)
MOCK_SLOT_CLAY = make_time_slot(
    court=MOCK_COURT_CLAY_OUTDOOR,
    start_time=_BASE_DT + timedelta(hours=3),
    status="free",
)

MOCK_TIME_SLOTS = [MOCK_SLOT_FREE, MOCK_SLOT_BOOKED, MOCK_SLOT_FOR_SALE, MOCK_SLOT_CLAY]

# ── Notification subscriptions ─────────────────────────────────────────────

MOCK_NOTIFICATION_CREATE = NotificationSubscriptionCreate(
    club_id="test-club",
    notify_on_statuses=["free", "for_sale"],
    is_recurring=True,
    days_of_week=["tuesday", "thursday"],
    time_from="18:00",
    time_to="21:00",
)

MOCK_SUBSCRIPTION = NotificationSubscription(
    id=_uuid("sub-1"),
    club_id="test-club",
    club_name="Test Tennis Club",
    notify_on_statuses=["free", "for_sale"],
    is_recurring=True,
    days_of_week=["tuesday", "thursday"],
    time_from="18:00",
    time_to="21:00",
    active=True,
    match_count=3,
    last_notified_at=None,
    created_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    updated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
)
