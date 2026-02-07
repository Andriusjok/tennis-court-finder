from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import PaginationParams, paginate
from app.generated.models import TimeSlotListResponse
from app.services.registry import registry

router = APIRouter(prefix="/api/clubs/{club_id}", tags=["time-slots"])


def _default_date_from() -> date:
    return date.today()


def _default_date_to() -> date:
    return date.today() + timedelta(days=7)


@router.get(
    "/time-slots",
    response_model=TimeSlotListResponse,
    operation_id="listClubTimeSlots",
    summary="List time slots across all courts of a club",
)
async def list_club_time_slots(
    club_id: str,
    pagination: PaginationParams = Depends(PaginationParams),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: str | None = Query(None),
    court_id: UUID | None = Query(None),
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
) -> TimeSlotListResponse:
    service = registry.get_service_or_404(club_id)
    slots = await service.list_time_slots(
        date_from=date_from or _default_date_from(),
        date_to=date_to or _default_date_to(),
        court_id=str(court_id) if court_id else None,
        status=status,
        surface_type=surface_type,
        court_type=court_type,
    )
    return paginate(slots, pagination, TimeSlotListResponse)


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
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: str | None = Query(None),
) -> TimeSlotListResponse:
    service = registry.get_service_or_404(club_id)
    slots = await service.list_time_slots(
        date_from=date_from or _default_date_from(),
        date_to=date_to or _default_date_to(),
        court_id=str(court_id),
        status=status,
    )
    return paginate(slots, pagination, TimeSlotListResponse)
