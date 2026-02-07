from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.generated.models import Court
from app.services.registry import registry

router = APIRouter(prefix="/api/clubs/{club_id}/courts", tags=["courts"])


@router.get(
    "",
    response_model=list[Court],
    operation_id="listCourts",
    summary="List courts for a club",
)
async def list_courts(
    club_id: str,
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
) -> list[Court]:
    service = registry.get_service_or_404(club_id)
    return await service.list_courts(surface_type=surface_type, court_type=court_type)


@router.get(
    "/{court_id}",
    response_model=Court,
    operation_id="getCourt",
    summary="Get details of a specific court",
)
async def get_court(club_id: str, court_id: UUID) -> Court:
    service = registry.get_service_or_404(club_id)
    court = await service.get_court(str(court_id))
    if court is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Court {court_id} not found in club {club_id}",
        )
    return court
