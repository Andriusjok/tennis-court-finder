"""
Notification subscription endpoints (authenticated).

All data is stored in SQLite via the app.db module.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import db
from app.dependencies import CurrentUser, PaginationParams
from app.generated.models import (
    NotificationLogListResponse,
    NotificationSubscription,
    NotificationSubscriptionCreate,
    NotificationSubscriptionListResponse,
    NotificationSubscriptionUpdate,
    NotificationToggle,
    PaginationMeta,
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


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
    subs = await db.list_subscriptions(
        current_user.email,
        active=active,
        club_id=club_id,
    )

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
    return await db.create_subscription(
        user_email=current_user.email,
        club_id=body.club_id,
        notify_on_statuses=body.notify_on_statuses,
        is_recurring=body.is_recurring,
        court_ids=body.court_ids,
        surface_types=body.surface_types,
        court_types=body.court_types,
        time_from=body.time_from,
        time_to=body.time_to,
        days_of_week=body.days_of_week,
        specific_dates=body.specific_dates,
        date_range_start=body.date_range_start,
        date_range_end=body.date_range_end,
    )


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
    sub = await db.get_subscription(str(notification_id))
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
    existing = await db.get_subscription(str(notification_id))
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    updated = await db.update_subscription(
        str(notification_id),
        club_id=body.club_id,
        notify_on_statuses=body.notify_on_statuses,
        is_recurring=body.is_recurring,
        court_ids=body.court_ids,
        surface_types=body.surface_types,
        court_types=body.court_types,
        time_from=body.time_from,
        time_to=body.time_to,
        days_of_week=body.days_of_week,
        specific_dates=body.specific_dates,
        date_range_start=body.date_range_start,
        date_range_end=body.date_range_end,
    )
    return updated  # type: ignore[return-value]


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
    deleted = await db.delete_subscription(str(notification_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )


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
    existing = await db.get_subscription(str(notification_id))
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    updated = await db.toggle_subscription(str(notification_id), body.active)
    return updated  # type: ignore[return-value]


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
    existing = await db.get_subscription(str(notification_id))
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification subscription {notification_id} not found",
        )

    logs = await db.list_logs(str(notification_id))
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
