"""
Low-level HTTP client for the tenisopasaulis.lt API.

Handles request construction, retries, and JSON ↔ Pydantic parsing.
Stateless – a single instance is shared across the app lifetime.
"""

from __future__ import annotations

import logging
from datetime import date

import httpx

from app.services.seb_arena.api_models import (
    AllPlacesInfoResponse,
    PlaceInfoBatchResponse,
    ValidIntervalResponse,
)
from app.services.seb_arena.config import (
    DEFAULT_HEADERS,
    PLACE_INFO_BATCH_URL,
    PLACES_INFO_URL,
    SALE_POINT,
    TENNIS_PLACE_IDS,
    VALID_INTERVAL_URL,
)

logger = logging.getLogger(__name__)

# Maximum number of dates per batch request (keep payloads small)
_MAX_DATES_PER_BATCH = 8


class SebArenaClient:
    """Async HTTP client for the SEB Arena / tenisopasaulis API."""

    def __init__(self, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # ── /api/v1/allPlacesInfo ─────────────────────────────────────────

    async def get_all_places(self) -> AllPlacesInfoResponse:
        """Fetch the list of all venues/places."""
        resp = await self._client.get(PLACES_INFO_URL)
        resp.raise_for_status()
        return AllPlacesInfoResponse.model_validate(resp.json())

    # ── /api/v1/placeInfoBatch ────────────────────────────────────────

    async def get_place_info_batch(
        self,
        dates: list[date],
        place_ids: list[int] | None = None,
        include_court_name: bool = True,
    ) -> PlaceInfoBatchResponse:
        """
        Fetch timetables for the given places and dates.

        If *place_ids* is None, all tennis places are queried.
        Dates are chunked into groups of _MAX_DATES_PER_BATCH if needed.
        """
        place_ids = place_ids or TENNIS_PLACE_IDS
        date_strs = [d.isoformat() for d in dates]

        # For now, single batch (the API handles up to ~14 days fine)
        payload = {
            "excludeCourtName": not include_court_name,
            "excludeInfoUrl": True,
            "places": place_ids,
            "dates": date_strs[:_MAX_DATES_PER_BATCH],
            "salePoint": SALE_POINT,
            "sessionToken": "",
        }

        logger.debug("placeInfoBatch request: places=%s dates=%s", place_ids, date_strs)
        resp = await self._client.post(PLACE_INFO_BATCH_URL, json=payload)
        resp.raise_for_status()
        return PlaceInfoBatchResponse.model_validate(resp.json())

    # ── /api/v2/sale-points/{id}/pricelists/valid-interval ────────────

    async def get_valid_interval(self) -> ValidIntervalResponse:
        """Fetch the valid booking date range for the sale point."""
        url = VALID_INTERVAL_URL.format(sale_point=SALE_POINT)
        resp = await self._client.get(url)
        resp.raise_for_status()
        return ValidIntervalResponse.model_validate(resp.json())
