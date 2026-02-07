"""
Notification subscription endpoints (authenticated).
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import CurrentUser, PaginationParams
from app.generated.models import (
    NotificationLog,
    NotificationLogListResponse,
    NotificationSubscription,
    NotificationSubscriptionCreate,
    NotificationSubscriptionListResponse,
    NotificationSubscriptionUpdate,
    NotificationToggle,
    PaginationMeta,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# ── In-memory mock store ──────────────────────────────────────────────────
# In production this would be a database-backed repository.
_MOCK_SUBSCRIPTIONS: dict[UUID, NotificationSubscription] = {}
_MOCK_LOGS: dict[UUID, list[NotificationLog]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── CRUD ──────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=NotificationSubscriptionListResponse,
    operation_id="listNotifications",
    summary="List the authenticated user's notification subscriptions",
)
async def list_notifications(
    current_user: CurrentUser,
    pagination: PaginationParams = Depends(PaginationParams),
    active: bool | None = Query(None, description="Filter by active/inactive"),
    club_id: str | None = Query(None, description="Filter by club slug"),
) -> NotificationSubscriptionListResponse:
    subs = list(_MOCK_SUBSCRIPTIONS.values())
    if active is not None:
        subs = [s for s in subs if s.active == active]
    if club_id is not None:
        subs = [s for s in subs if s.club_id == club_id]

    total = len(subs)
    start = pagination.offset
    end = start + pagination.page_size
    return NotificationSubscriptionListResponse(
        items=subs[start:end],
        meta=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=max(1, -(-total // pagination.page_size)),
        ),
    )


@router.post(
    "",
    response_model=NotificationSubscription,
    status_code=status.HTTP_201_CREATED,
    operation_id="createNotification",
    summary="Create a new notification subscription",
)
async def create_notification(
    body: NotificationSubscriptionCreate,
    current_user: CurrentUser,
) -> NotificationSubscription:
    now = _now()
    sub = NotificationSubscription(
        id=uuid4(),
        club_id=body.club_id,
        club_name=None,  # Would be looked up from club service
        court_ids=body.court_ids,
        surface_types=body.surface_types,
        court_types=body.court_types,
        notify_on_statuses=body.notify_on_statuses,
        time_from=body.time_from,
        time_to=body.time_to,
        is_recurring=body.is_recurring,
        days_of_week=body.days_of_week,
        specific_dates=body.specific_dates,
        date_range_start=body.date_range_start,
        date_range_end=body.date_range_end,
        active=True,
        match_count=0,
        last_notified_at=None,
        created_at=now,
        updated_at=now,
    )
    _MOCK_SUBSCRIPTIONS[sub.id] = sub
    return sub


@router.get(
    "/{notification_id}",
    response_model=NotificationSubscription,
    operation_id="getNotification",
    summary="Get a specific notification subscription",
)
async def get_notification(
    notification_id: UUID,
    current_user: CurrentUser,
) -> NotificationSubscription:
    sub = _MOCK_SUBSCRIPTIONS.get(notification_id)
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )
    return sub


@router.put(
    "/{notification_id}",
    response_model=NotificationSubscription,
    operation_id="updateNotification",
    summary="Fully update a notification subscription",
)
async def update_notification(
    notification_id: UUID,
    body: NotificationSubscriptionUpdate,
    current_user: CurrentUser,
) -> NotificationSubscription:
    existing = _MOCK_SUBSCRIPTIONS.get(notification_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    updated = existing.model_copy(
        update={
            **body.model_dump(),
            "updated_at": _now(),
        }
    )
    _MOCK_SUBSCRIPTIONS[notification_id] = updated
    return updated


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteNotification",
    summary="Delete a notification subscription",
)
async def delete_notification(
    notification_id: UUID,
    current_user: CurrentUser,
) -> None:
    if notification_id not in _MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )
    del _MOCK_SUBSCRIPTIONS[notification_id]


@router.patch(
    "/{notification_id}/toggle",
    response_model=NotificationSubscription,
    operation_id="toggleNotification",
    summary="Activate or deactivate a notification subscription",
)
async def toggle_notification(
    notification_id: UUID,
    body: NotificationToggle,
    current_user: CurrentUser,
) -> NotificationSubscription:
    existing = _MOCK_SUBSCRIPTIONS.get(notification_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    updated = existing.model_copy(
        update={"active": body.active, "updated_at": _now()}
    )
    _MOCK_SUBSCRIPTIONS[notification_id] = updated
    return updated


@router.get(
    "/{notification_id}/logs",
    response_model=NotificationLogListResponse,
    operation_id="listNotificationLogs",
    summary="List sent notification logs for a subscription",
)
async def list_notification_logs(
    notification_id: UUID,
    current_user: CurrentUser,
    pagination: PaginationParams = Depends(PaginationParams),
) -> NotificationLogListResponse:
    if notification_id not in _MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    logs = _MOCK_LOGS.get(notification_id, [])
    total = len(logs)
    start = pagination.offset
    end = start + pagination.page_size
    return NotificationLogListResponse(
        items=logs[start:end],
        meta=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=max(1, -(-total // pagination.page_size)),
        ),
    )
