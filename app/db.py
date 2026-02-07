from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import aiosqlite

from app.config import DB_PATH
from app.generated.models import (
    NotificationLog,
    NotificationSubscription,
    TimeSlot,
)

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _db
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(db_path))
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")
    await _db.executescript(_SCHEMA)
    await _db.commit()
    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    assert _db is not None, "Database not initialized — call init_db() first"
    return _db


_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id              TEXT PRIMARY KEY,
    user_email      TEXT NOT NULL,
    club_id         TEXT NOT NULL,
    club_name       TEXT,
    court_ids       TEXT,
    surface_types   TEXT,
    court_types     TEXT,
    notify_on_statuses TEXT NOT NULL,
    time_from       TEXT,
    time_to         TEXT,
    is_recurring    INTEGER NOT NULL DEFAULT 0,
    days_of_week    TEXT,
    specific_dates  TEXT,
    date_range_start TEXT,
    date_range_end  TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    match_count     INTEGER NOT NULL DEFAULT 0,
    last_notified_at TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_email);
CREATE INDEX IF NOT EXISTS idx_subs_active ON subscriptions(active);

CREATE TABLE IF NOT EXISTS notification_logs (
    id              TEXT PRIMARY KEY,
    subscription_id TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'email',
    time_slot_json  TEXT NOT NULL,
    status          TEXT,
    error_message   TEXT,
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_sub ON notification_logs(subscription_id);

CREATE TABLE IF NOT EXISTS otp_codes (
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (email, code)
);
"""


def _json_or_none(value: list | None) -> str | None:
    if value is None:
        return None
    return json.dumps([str(v) for v in value])


def _from_json(raw: str | None) -> list | None:
    if raw is None:
        return None
    return json.loads(raw)


def _iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_subscription(row: aiosqlite.Row) -> NotificationSubscription:
    return NotificationSubscription(
        id=UUID(row["id"]),
        club_id=row["club_id"],
        club_name=row["club_name"],
        court_ids=_from_json(row["court_ids"]),
        surface_types=_from_json(row["surface_types"]),
        court_types=_from_json(row["court_types"]),
        notify_on_statuses=json.loads(row["notify_on_statuses"]),
        time_from=row["time_from"],
        time_to=row["time_to"],
        is_recurring=bool(row["is_recurring"]),
        days_of_week=_from_json(row["days_of_week"]),
        specific_dates=_from_json(row["specific_dates"]),
        date_range_start=row["date_range_start"],
        date_range_end=row["date_range_end"],
        active=bool(row["active"]),
        match_count=row["match_count"],
        last_notified_at=row["last_notified_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_log(row: aiosqlite.Row) -> NotificationLog:
    return NotificationLog(
        id=UUID(row["id"]),
        subscription_id=UUID(row["subscription_id"]),
        sent_at=row["sent_at"],
        channel=row["channel"],
        time_slot=TimeSlot.model_validate_json(row["time_slot_json"]),
        status=row["status"],
        error_message=row["error_message"],
    )


# ── Subscriptions ──────────────────────────────────────────────────────────


async def create_subscription(
    user_email: str,
    club_id: str,
    notify_on_statuses: list[str],
    is_recurring: bool,
    *,
    club_name: str | None = None,
    court_ids: list[UUID] | None = None,
    surface_types: list[str] | None = None,
    court_types: list[str] | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    days_of_week: list[str] | None = None,
    specific_dates: list[date] | None = None,
    date_range_start: date | None = None,
    date_range_end: date | None = None,
) -> NotificationSubscription:
    conn = get_db()
    sub_id = str(uuid4())
    now = _now_iso()

    await conn.execute(
        """
        INSERT INTO subscriptions (
            id, user_email, club_id, club_name,
            court_ids, surface_types, court_types, notify_on_statuses,
            time_from, time_to,
            is_recurring, days_of_week, specific_dates,
            date_range_start, date_range_end,
            active, match_count, last_notified_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, NULL, ?, ?)
        """,
        (
            sub_id,
            user_email,
            club_id,
            club_name,
            _json_or_none(court_ids),
            _json_or_none(surface_types),
            _json_or_none(court_types),
            json.dumps(notify_on_statuses),
            time_from,
            time_to,
            int(is_recurring),
            _json_or_none(days_of_week),
            _json_or_none(specific_dates),
            _iso(date_range_start),
            _iso(date_range_end),
            now,
            now,
        ),
    )
    await conn.commit()
    return await get_subscription(sub_id)  # type: ignore[return-value]


async def get_subscription(sub_id: str) -> NotificationSubscription | None:
    conn = get_db()
    async with conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)) as cur:
        row = await cur.fetchone()
    return _row_to_subscription(row) if row else None


async def list_subscriptions(
    user_email: str,
    *,
    active: bool | None = None,
    club_id: str | None = None,
) -> list[NotificationSubscription]:
    conn = get_db()
    sql = "SELECT * FROM subscriptions WHERE user_email = ?"
    params: list = [user_email]

    if active is not None:
        sql += " AND active = ?"
        params.append(int(active))
    if club_id is not None:
        sql += " AND club_id = ?"
        params.append(club_id)

    sql += " ORDER BY created_at DESC"

    async with conn.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [_row_to_subscription(r) for r in rows]


async def list_active_subscriptions() -> list[tuple[str, NotificationSubscription]]:
    conn = get_db()
    async with conn.execute("SELECT * FROM subscriptions WHERE active = 1") as cur:
        rows = await cur.fetchall()
    return [(row["user_email"], _row_to_subscription(row)) for row in rows]


async def update_subscription(
    sub_id: str,
    *,
    club_id: str,
    notify_on_statuses: list[str],
    is_recurring: bool,
    court_ids: list[UUID] | None = None,
    surface_types: list[str] | None = None,
    court_types: list[str] | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    days_of_week: list[str] | None = None,
    specific_dates: list[date] | None = None,
    date_range_start: date | None = None,
    date_range_end: date | None = None,
) -> NotificationSubscription | None:
    conn = get_db()
    now = _now_iso()
    await conn.execute(
        """
        UPDATE subscriptions SET
            club_id = ?, notify_on_statuses = ?, is_recurring = ?,
            court_ids = ?, surface_types = ?, court_types = ?,
            time_from = ?, time_to = ?,
            days_of_week = ?, specific_dates = ?,
            date_range_start = ?, date_range_end = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            club_id,
            json.dumps(notify_on_statuses),
            int(is_recurring),
            _json_or_none(court_ids),
            _json_or_none(surface_types),
            _json_or_none(court_types),
            time_from,
            time_to,
            _json_or_none(days_of_week),
            _json_or_none(specific_dates),
            _iso(date_range_start),
            _iso(date_range_end),
            now,
            sub_id,
        ),
    )
    await conn.commit()
    return await get_subscription(sub_id)


async def toggle_subscription(sub_id: str, active: bool) -> NotificationSubscription | None:
    conn = get_db()
    now = _now_iso()
    await conn.execute(
        "UPDATE subscriptions SET active = ?, updated_at = ? WHERE id = ?",
        (int(active), now, sub_id),
    )
    await conn.commit()
    return await get_subscription(sub_id)


async def delete_subscription(sub_id: str) -> bool:
    conn = get_db()
    cur = await conn.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    await conn.commit()
    return cur.rowcount > 0


async def bump_match_count(sub_id: str) -> None:
    conn = get_db()
    now = _now_iso()
    await conn.execute(
        """
        UPDATE subscriptions
        SET match_count = match_count + 1, last_notified_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, sub_id),
    )
    await conn.commit()


# ── Notification logs ──────────────────────────────────────────────────────


async def create_log(
    subscription_id: str,
    time_slot: TimeSlot,
    *,
    channel: str = "email",
    status: str = "sent",
    error_message: str | None = None,
) -> NotificationLog:
    conn = get_db()
    log_id = str(uuid4())
    now = _now_iso()

    await conn.execute(
        """
        INSERT INTO notification_logs
            (id, subscription_id, sent_at, channel, time_slot_json, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            subscription_id,
            now,
            channel,
            time_slot.model_dump_json(),
            status,
            error_message,
        ),
    )
    await conn.commit()

    return NotificationLog(
        id=UUID(log_id),
        subscription_id=UUID(subscription_id),
        sent_at=now,
        channel=channel,
        time_slot=time_slot,
        status=status,
        error_message=error_message,
    )


async def list_logs(subscription_id: str) -> list[NotificationLog]:
    conn = get_db()
    async with conn.execute(
        "SELECT * FROM notification_logs WHERE subscription_id = ? ORDER BY sent_at DESC",
        (subscription_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_log(r) for r in rows]


# ── OTP codes ──────────────────────────────────────────────────────────────


async def create_otp(email: str, code: str, ttl_seconds: int = 300) -> None:
    conn = get_db()
    await conn.execute("DELETE FROM otp_codes WHERE email = ? AND used = 0", (email,))
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=ttl_seconds)
    await conn.execute(
        "INSERT INTO otp_codes (email, code, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (email, code, now.isoformat(), expires_at.isoformat()),
    )
    await conn.commit()


async def verify_otp(email: str, code: str) -> bool:
    conn = get_db()
    now = datetime.now(UTC).isoformat()
    async with conn.execute(
        """
        SELECT rowid FROM otp_codes
        WHERE email = ? AND code = ? AND used = 0 AND expires_at > ?
        """,
        (email, code, now),
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        return False

    await conn.execute(
        "UPDATE otp_codes SET used = 1 WHERE email = ? AND code = ?",
        (email, code),
    )
    await conn.commit()
    return True


async def cleanup_expired_otps() -> None:
    conn = get_db()
    now = datetime.now(UTC).isoformat()
    await conn.execute("DELETE FROM otp_codes WHERE expires_at < ?", (now,))
    await conn.commit()
