from __future__ import annotations

from pydantic import BaseModel


class PlaceInfo(BaseModel):
    id: int
    placeName: str
    placeInfo: str


class AllPlacesInfoResponse(BaseModel):
    status: str
    data: list[PlaceInfo]


class SlotEntry(BaseModel):
    from_: str  # "HH:MM:SS"
    to: str  # "HH:MM:SS"
    status: str  # "free" | "full" | "fullsell"

    class Config:
        populate_by_name = True

    def __init__(self, **data):
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)


class CourtTimetable(BaseModel):
    courtID: int
    courtName: str | None = None
    infoUrl: str | None = None
    date: str  # "YYYY-MM-DD"
    timetable: dict[str, SlotEntry]


class PlaceData(BaseModel):
    place: int
    data: list[list[CourtTimetable]]


class PlaceInfoBatchResponse(BaseModel):
    status: str
    data: list[PlaceData]


class ValidIntervalData(BaseModel):
    from_: str | None = None
    till: str | None = None

    def __init__(self, **data):
        if "from" in data:
            data["from_"] = data.pop("from")
        super().__init__(**data)


class ValidIntervalResponse(BaseModel):
    status: str
    data: ValidIntervalData
