"""
Pydantic models that mirror the tenisopasaulis.lt API response shapes.

These are *internal* – the rest of the app never imports them directly.
The SebArenaService translates them into app.generated.models.
"""

from __future__ import annotations

from pydantic import BaseModel


# ── /api/v1/allPlacesInfo ─────────────────────────────────────────────────

class PlaceInfo(BaseModel):
    id: int
    placeName: str
    placeInfo: str  # URL


class AllPlacesInfoResponse(BaseModel):
    status: str
    data: list[PlaceInfo]


# ── /api/v1/placeInfoBatch ────────────────────────────────────────────────

class SlotEntry(BaseModel):
    """A single 30-minute slot within a court's timetable."""
    from_: str  # "HH:MM:SS"  (aliased from `from` which is a Python keyword)
    to: str     # "HH:MM:SS"
    status: str  # "free" | "full" | "fullsell"

    class Config:
        # The JSON field is "from" – map it to from_
        populate_by_name = True

    def __init__(self, **data):
        # Handle the fact that "from" is a Python keyword
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)


class CourtTimetable(BaseModel):
    """Timetable for one court on one date."""
    courtID: int
    courtName: str | None = None
    infoUrl: str | None = None
    date: str  # "YYYY-MM-DD"
    timetable: dict[str, SlotEntry]  # key = "HH:MM:SS"


class PlaceData(BaseModel):
    """Response data for one place."""
    place: int
    data: list[list[CourtTimetable]]  # nested list (one list per date)


class PlaceInfoBatchResponse(BaseModel):
    status: str
    data: list[PlaceData]


# ── /api/v2/sale-points/{id}/pricelists/valid-interval ────────────────────

class ValidIntervalData(BaseModel):
    from_: str | None = None  # "YYYY-MM-DD"
    till: str | None = None   # "YYYY-MM-DD"

    def __init__(self, **data):
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)


class ValidIntervalResponse(BaseModel):
    status: str
    data: ValidIntervalData
