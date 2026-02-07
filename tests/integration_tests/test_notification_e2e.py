from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app import db
from app.generated.models import Club, Court, TimeSlot
from app.services.cache import CachedClubService
from app.services.notifier import SlotNotifier
from app.services.registry import ClubRegistry
from tests.mocks.models import _uuid
from tests.mocks.services import MockClubService

_CLUB = Club(
    id="test-club",
    name="Test Tennis Club",
    address="123 Racket Lane",
    city="Vilnius",
    phone="+37060000000",
    website="https://test-tennis.lt",
    image_url=None,
    courts_count=2,
)

_COURT_1 = Court(
    id=_uuid("e2e-court-1"),
    club_id="test-club",
    name="Centre Court",
    surface_type="hard",
    court_type="indoor",
    description="Main court",
)

_COURT_2 = Court(
    id=_uuid("e2e-court-2"),
    club_id="test-club",
    name="Court B",
    surface_type="clay",
    court_type="outdoor",
    description=None,
)

_TODAY = date.today()
_BASE_DT = datetime(_TODAY.year, _TODAY.month, _TODAY.day, 18, 0, tzinfo=UTC)


def _make_slot(
    court: Court,
    offset_hours: int = 0,
    status: str = "booked",
) -> TimeSlot:
    st = _BASE_DT + timedelta(hours=offset_hours)
    return TimeSlot(
        id=_uuid(f"e2e-slot-{court.id}-{st.isoformat()}"),
        court_id=court.id,
        club_id=court.club_id,
        court_name=court.name,
        surface_type=court.surface_type,
        court_type=court.court_type,
        start_time=st,
        end_time=st + timedelta(hours=1),
        duration_minutes=60,
        status=status,
        price=30.0,
        currency="EUR",
    )


_SLOT_1_BOOKED = _make_slot(_COURT_1, offset_hours=0, status="booked")
_SLOT_2_BOOKED = _make_slot(_COURT_1, offset_hours=1, status="booked")
_SLOT_3_BOOKED = _make_slot(_COURT_2, offset_hours=0, status="booked")

_SLOT_1_FREE = _SLOT_1_BOOKED.model_copy(update={"status": "free"})
_SLOT_3_FREE = _SLOT_3_BOOKED.model_copy(update={"status": "free"})


def _build_registry_with_cache(courts: list[Court], slots: list[TimeSlot]) -> ClubRegistry:
    mock_svc = MockClubService(club=_CLUB, courts=courts, time_slots=slots)
    cached = CachedClubService(mock_svc, refresh_interval_seconds=9999)
    cached._cache.update(courts, slots)

    reg = ClubRegistry()
    reg._services[_CLUB.id] = cached
    reg._clients = []
    return reg


@pytest.fixture()
async def _init_db(tmp_path, monkeypatch):
    import app.db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", str(tmp_path / "e2e_test.db"))
    await db.init_db()
    yield
    await db.close_db()


@pytest.mark.asyncio
async def test_full_notification_pipeline(_init_db, monkeypatch):
    sub = await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        club_name="Test Tennis Club",
        notify_on_statuses=["free"],
        is_recurring=False,
        time_from="17:00",
        time_to="20:00",
    )
    assert sub.active is True
    assert sub.match_count == 0
    assert sub.last_notified_at is None

    initial_slots = [_SLOT_1_BOOKED, _SLOT_2_BOOKED, _SLOT_3_BOOKED]
    test_registry = _build_registry_with_cache(
        courts=[_COURT_1, _COURT_2],
        slots=initial_slots,
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    assert len(notifier._prev_snapshot) == 3
    assert all(s == "booked" for s in notifier._prev_snapshot.values())

    updated_slots = [_SLOT_1_FREE, _SLOT_2_BOOKED, _SLOT_3_FREE]
    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1, _COURT_2], updated_slots)

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 1
    call_args = mock_send_email.call_args

    assert call_args[0][0] == "user@example.com"
    assert call_args[0][1] == "Test Tennis Club"

    notified_slots: list[TimeSlot] = call_args[0][2]
    assert len(notified_slots) == 2
    notified_ids = {s.id for s in notified_slots}
    assert _SLOT_1_FREE.id in notified_ids
    assert _SLOT_3_FREE.id in notified_ids

    logs = await db.list_logs(str(sub.id))
    assert len(logs) == 2
    assert all(log.status == "sent" for log in logs)
    assert all(log.subscription_id == sub.id for log in logs)

    updated_sub = await db.get_subscription(str(sub.id))
    assert updated_sub is not None
    assert updated_sub.match_count == 1
    assert updated_sub.last_notified_at is not None


@pytest.mark.asyncio
async def test_no_notification_when_no_matching_subscription(_init_db, monkeypatch):
    await db.create_subscription(
        user_email="user@example.com",
        club_id="other-club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    # Slot becomes free at test-club but subscription is for other-club
    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_inactive_subscription_skipped(_init_db, monkeypatch):
    sub = await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )
    await db.toggle_subscription(str(sub.id), active=False)

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_cooldown_prevents_repeated_notification(_init_db, monkeypatch):
    monkeypatch.setattr("app.services.notifier.NOTIFIER_COOLDOWN", 600)

    await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    # First tick: slot becomes free → notification sent
    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 1

    # Second tick: another slot becomes free → skipped due to cooldown
    slot_2_free = _SLOT_2_BOOKED.model_copy(update={"status": "free"})
    svc._cache.update([_COURT_1], [_SLOT_1_FREE, slot_2_free])

    mock_send_email.reset_mock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_email_failure_logged(_init_db, monkeypatch):
    sub = await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock(side_effect=ConnectionError("SMTP unreachable"))
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    logs = await db.list_logs(str(sub.id))
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert "SMTP unreachable" in (logs[0].error_message or "")


@pytest.mark.asyncio
async def test_time_filter_excludes_outside_range(_init_db, monkeypatch):
    # Subscription only wants 20:00–22:00, slot is at 18:00
    await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
        time_from="20:00",
        time_to="22:00",
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_recurring_day_filter(_init_db, monkeypatch):
    today_name = _TODAY.strftime("%A").lower()
    other_day = "monday" if today_name != "monday" else "tuesday"

    await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=True,
        days_of_week=[other_day],
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    # Today is not the subscribed day → no match
    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_surface_type_filter(_init_db, monkeypatch):
    await db.create_subscription(
        user_email="user@example.com",
        club_id="test-club",
        notify_on_statuses=["free"],
        is_recurring=False,
        surface_types=["clay"],
    )

    # _SLOT_1 is on _COURT_1 which is hard/indoor
    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 0


@pytest.mark.asyncio
async def test_multiple_users_notified_independently(_init_db, monkeypatch):
    await db.create_subscription(
        user_email="alice@example.com",
        club_id="test-club",
        club_name="Test Tennis Club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )
    await db.create_subscription(
        user_email="bob@example.com",
        club_id="test-club",
        club_name="Test Tennis Club",
        notify_on_statuses=["free"],
        is_recurring=False,
    )

    test_registry = _build_registry_with_cache(
        courts=[_COURT_1],
        slots=[_SLOT_1_BOOKED],
    )
    monkeypatch.setattr("app.services.notifier.registry", test_registry)

    notifier = SlotNotifier()
    notifier._prev_snapshot = notifier._take_snapshot()

    svc = test_registry._services["test-club"]
    svc._cache.update([_COURT_1], [_SLOT_1_FREE])

    mock_send_email = AsyncMock()
    with patch("app.services.notifier.send_notification_email", mock_send_email):
        await notifier._tick()

    assert mock_send_email.call_count == 2
    recipients = {call.args[0] for call in mock_send_email.call_args_list}
    assert recipients == {"alice@example.com", "bob@example.com"}
