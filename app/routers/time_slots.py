"""
Time slot endpoints – availability for courts.
"""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status


from app.dependencies import PaginationParams
from app.generated.models import (
    PaginationMeta,
    TimeSlotListResponse,
)
from app.services.registry import registry

router = APIRouter(prefix="/api/clubs/{club_id}", tags=["time-slots"])


def _default_date_from() -> date:
    return date.today()


def _default_date_to() -> date:
    return date.today() + timedelta(days=7)


def _paginate(
    items: list, pagination: PaginationParams
) -> TimeSlotListResponse:
    total = len(items)
    start = pagination.offset
    end = start + pagination.page_size
    return TimeSlotListResponse(
        items=items[start:end],
        meta=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=max(1, -(-total // pagination.page_size)),
        ),
    )


@router.get(
    "/time-slots",
    response_model=TimeSlotListResponse,
    operation_id="listClubTimeSlots",
    summary="List time slots across all courts of a club",
)
async def list_club_time_slots(
    club_id: str,
    pagination: PaginationParams = Depends(PaginationParams),
    date_from: date | None = Query(None, description="Start date (inclusive, defaults to today)"),
    date_to: date | None = Query(None, description="End date (inclusive, defaults to +7 days)"),
    status: str | None = Query(None, description="Filter by slot status"),
    court_id: UUID | None = Query(None, description="Filter by court"),
    surface_type: str | None = Query(None, description="Filter by surface"),
    court_type: str | None = Query(None, description="Filter by indoor/outdoor"),
) -> TimeSlotListResponse:
    service = registry.get_service(club_id)
    if service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Club {club_id} not found",
        )

    slots = await service.list_time_slots(
        date_from=date_from or _default_date_from(),
        date_to=date_to or _default_date_to(),
        court_id=str(court_id) if court_id else None,
        status=status,
        surface_type=surface_type,
        court_type=court_type,
    )
    return _paginate(slots, pagination)


@router.get(
    "/courts/{court_id}/time-slots",
    response_model=TimeSlotListResponse,
    operation_id="listCourtTimeSlots",
    summary="List time slots for a specific court",
)
async def list_court_time_slots(
    club_id: str,
    court_id: UUID,
    pagination: PaginationParams = Depends(PaginationParams),
    date_from: date | None = Query(None, description="Start date (inclusive, defaults to today)"),
    date_to: date | None = Query(None, description="End date (inclusive, defaults to +7 days)"),
    status: str | None = Query(None, description="Filter by slot status"),
) -> TimeSlotListResponse:
    service = registry.get_service(club_id)
    if service is None:
        raise HTTPException(
            status_code=404,
            detail=f"Club {club_id} not found",
        )

    slots = await service.list_time_slots(
        date_from=date_from or _default_date_from(),
        date_to=date_to or _default_date_to(),
        court_id=str(court_id),
        status=status,
    )
    return _paginate(slots, pagination)
