"""
SQLite database layer using aiosqlite.

Stores notification subscriptions and notification logs.
Tables are created automatically on first connect.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
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

# ── Module-level connection ───────────────────────────────────────────────

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Open the database and create tables if they don't exist."""
    global _db
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    _db = await aiosqlite.connect(str(db_path))
    _db.row_factory = aiosqlite.Row  # dict-like rows
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    await _db.executescript(_SCHEMA)
    await _db.commit()
    logger.info("Database initialized at %s", db_path)


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")


def get_db() -> aiosqlite.Connection:
    """Return the active database connection (must call init_db first)."""
    assert _db is not None, "Database not initialized — call init_db() first"
    return _db


# ── Schema ────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id              TEXT PRIMARY KEY,
    user_email      TEXT NOT NULL,
    club_id         TEXT NOT NULL,
    club_name       TEXT,
    court_ids       TEXT,           -- JSON array of UUID strings
    surface_types   TEXT,           -- JSON array
    court_types     TEXT,           -- JSON array
    notify_on_statuses TEXT NOT NULL, -- JSON array
    time_from       TEXT,
    time_to         TEXT,
    is_recurring    INTEGER NOT NULL DEFAULT 0,
    days_of_week    TEXT,           -- JSON array
    specific_dates  TEXT,           -- JSON array of ISO date strings
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
"""


# ── Helpers ───────────────────────────────────────────────────────────────


def _json_or_none(value: list | None) -> str | None:
    """Serialize a list to JSON or return None."""
    if value is None:
        return None
    return json.dumps([str(v) for v in value])


def _from_json(raw: str | None) -> list | None:
    """Parse a JSON string back to a list, or return None."""
    if raw is None:
        return None
    return json.loads(raw)


def _iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_subscription(row: aiosqlite.Row) -> NotificationSubscription:
    """Convert a database row to a NotificationSubscription model."""
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
    """Convert a database row to a NotificationLog model."""
    return NotificationLog(
        id=UUID(row["id"]),
        subscription_id=UUID(row["subscription_id"]),
        sent_at=row["sent_at"],
        channel=row["channel"],
        time_slot=TimeSlot.model_validate_json(row["time_slot_json"]),
        status=row["status"],
        error_message=row["error_message"],
    )


# ══════════════════════════════════════════════════════════════════════════
#                    SUBSCRIPTION REPOSITORY
# ══════════════════════════════════════════════════════════════════════════


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
    """Insert a new subscription and return it."""
    db = get_db()
    sub_id = str(uuid4())
    now = _now_iso()

    await db.execute(
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
            sub_id, user_email, club_id, club_name,
            _json_or_none(court_ids),
            _json_or_none(surface_types),
            _json_or_none(court_types),
            json.dumps(notify_on_statuses),
            time_from, time_to,
            int(is_recurring),
            _json_or_none(days_of_week),
            _json_or_none(specific_dates),
            _iso(date_range_start), _iso(date_range_end),
            now, now,
        ),
    )
    await db.commit()
    return await get_subscription(sub_id)  # type: ignore[return-value]


async def get_subscription(sub_id: str) -> NotificationSubscription | None:
    """Fetch a single subscription by ID."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM subscriptions WHERE id = ?", (sub_id,)
    ) as cur:
        row = await cur.fetchone()
    return _row_to_subscription(row) if row else None


async def list_subscriptions(
    user_email: str,
    *,
    active: bool | None = None,
    club_id: str | None = None,
) -> list[NotificationSubscription]:
    """List subscriptions for a user, with optional filters."""
    db = get_db()
    sql = "SELECT * FROM subscriptions WHERE user_email = ?"
    params: list = [user_email]

    if active is not None:
        sql += " AND active = ?"
        params.append(int(active))
    if club_id is not None:
        sql += " AND club_id = ?"
        params.append(club_id)

    sql += " ORDER BY created_at DESC"

    async with db.execute(sql, params) as cur:
        rows = await cur.fetchall()
    return [_row_to_subscription(r) for r in rows]


async def list_active_subscriptions() -> list[tuple[str, NotificationSubscription]]:
    """
    Return all active subscriptions across all users.

    Returns a list of (user_email, subscription) tuples.
    """
    db = get_db()
    async with db.execute(
        "SELECT * FROM subscriptions WHERE active = 1"
    ) as cur:
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
    """Update an existing subscription."""
    db = get_db()
    now = _now_iso()
    await db.execute(
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
            time_from, time_to,
            _json_or_none(days_of_week),
            _json_or_none(specific_dates),
            _iso(date_range_start), _iso(date_range_end),
            now, sub_id,
        ),
    )
    await db.commit()
    return await get_subscription(sub_id)


async def toggle_subscription(sub_id: str, active: bool) -> NotificationSubscription | None:
    """Activate or deactivate a subscription."""
    db = get_db()
    now = _now_iso()
    await db.execute(
        "UPDATE subscriptions SET active = ?, updated_at = ? WHERE id = ?",
        (int(active), now, sub_id),
    )
    await db.commit()
    return await get_subscription(sub_id)


async def delete_subscription(sub_id: str) -> bool:
    """Delete a subscription. Returns True if a row was actually deleted."""
    db = get_db()
    cur = await db.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    await db.commit()
    return cur.rowcount > 0


async def bump_match_count(sub_id: str) -> None:
    """Increment match_count and set last_notified_at to now."""
    db = get_db()
    now = _now_iso()
    await db.execute(
        """
        UPDATE subscriptions
        SET match_count = match_count + 1, last_notified_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, sub_id),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════════════════════
#                    NOTIFICATION LOG REPOSITORY
# ══════════════════════════════════════════════════════════════════════════


async def create_log(
    subscription_id: str,
    time_slot: TimeSlot,
    *,
    channel: str = "email",
    status: str = "sent",
    error_message: str | None = None,
) -> NotificationLog:
    """Record a sent (or failed) notification."""
    db = get_db()
    log_id = str(uuid4())
    now = _now_iso()

    await db.execute(
        """
        INSERT INTO notification_logs
            (id, subscription_id, sent_at, channel, time_slot_json, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id, subscription_id, now, channel,
            time_slot.model_dump_json(),
            status, error_message,
        ),
    )
    await db.commit()

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
    """Return notification logs for a subscription, newest first."""
    db = get_db()
    async with db.execute(
        "SELECT * FROM notification_logs WHERE subscription_id = ? ORDER BY sent_at DESC",
        (subscription_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_log(r) for r in rows]
