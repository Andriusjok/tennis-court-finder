from fastapi import APIRouter, Depends

from app.dependencies import PaginationParams, paginate
from app.generated.models import Club, ClubListResponse
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
    city: str | None = None,
) -> ClubListResponse:
    clubs = registry.list_clubs()
    if city:
        clubs = [c for c in clubs if city.lower() in c.city.lower()]
    return paginate(clubs, pagination, ClubListResponse)


@router.get(
    "/{club_id}",
    response_model=Club,
    operation_id="getClub",
    summary="Get details of a specific club",
)
async def get_club(club_id: str) -> Club:
    service = registry.get_service_or_404(club_id)
    club = service.get_club()
    courts = await service.list_courts()
    return club.model_copy(update={"courts_count": len(courts)})
