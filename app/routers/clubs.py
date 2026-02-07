"""
Tennis club endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import PaginationParams
from app.generated.models import (
    Club,
    ClubListResponse,
    PaginationMeta,
)
from app.services.registry import registry

router = APIRouter(prefix="/api/clubs", tags=["clubs"])


@router.get(
    "",
    response_model=ClubListResponse,
    operation_id="listClubs",
    summary="List all integrated tennis clubs",
)
async def list_clubs(
    pagination: PaginationParams = Depends(PaginationParams),
    city: str | None = Query(None, description="Filter by city (case-insensitive)"),
) -> ClubListResponse:
    clubs = registry.list_clubs()
    if city:
        clubs = [c for c in clubs if city.lower() in c.city.lower()]

    total = len(clubs)
    start = pagination.offset
    end = start + pagination.page_size
    page_items = clubs[start:end]

    return ClubListResponse(
        items=page_items,
        meta=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=max(1, -(-total // pagination.page_size)),
        ),
    )


@router.get(
    "/{club_id}",
    response_model=Club,
    operation_id="getClub",
    summary="Get details of a specific club",
)
async def get_club(club_id: str) -> Club:
    service = registry.get_service(club_id)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Club {club_id} not found",
        )
    club = service.get_club()
    # Enrich with court count
    courts = await service.list_courts()
    club = club.model_copy(update={"courts_count": len(courts)})
    return club
