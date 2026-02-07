"""
Health check endpoint.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.generated.models import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    operation_id="getHealth",
    summary="Health check",
)
async def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )
