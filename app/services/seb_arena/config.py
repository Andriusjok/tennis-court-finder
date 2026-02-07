from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

BASE_URL = "https://ws.tenisopasaulis.lt"
WP_API_URL = "https://api.sebarena.lt"

PLACES_INFO_URL = f"{BASE_URL}/api/v1/allPlacesInfo"
PLACE_INFO_BATCH_URL = f"{BASE_URL}/api/v1/placeInfoBatch"
VALID_INTERVAL_URL = f"{BASE_URL}/api/v2/sale-points/{{sale_point}}/pricelists/valid-interval"
SAVITARNA_OPTIONS_URL = f"{WP_API_URL}/wp-json/data/v1/get_savitarna_options/"

SALE_POINT = 11

CLUB_ID = "seb-arena"
CLUB_UUID_NS = UUID("10000000-0000-0000-0000-00000000eb01")
CLUB_NAME = "SEB Arena"
CLUB_ADDRESS = "Ąžuolyno g. 7"
CLUB_CITY = "Vilnius"
CLUB_PHONE = "+37052323636"
CLUB_WEBSITE = "https://book.sebarena.lt/#/rezervuoti/tenisas"

TENNIS_PLACE_IDS: list[int] = [2, 18, 5, 20, 8]


@dataclass(frozen=True)
class PlaceMapping:
    surface_type: str
    court_type: str


# place-id → surface/type (from allPlacesInfo):
#   2  = Vidaus hard           → indoor hard
#   18 = Vidaus hard plėtra    → indoor hard (expansion halls)
#   5  = Bernardinai gruntas   → outdoor clay
#   20 = Bernardinai sint. žolė → outdoor artificial_grass
#   8  = Kilimas               → indoor carpet
PLACE_MAPPINGS: dict[int, PlaceMapping] = {
    2: PlaceMapping(surface_type="hard", court_type="indoor"),
    18: PlaceMapping(surface_type="hard", court_type="indoor"),
    5: PlaceMapping(surface_type="clay", court_type="outdoor"),
    20: PlaceMapping(surface_type="artificial_grass", court_type="outdoor"),
    8: PlaceMapping(surface_type="carpet", court_type="indoor"),
}

# tenisopasaulis status → our SlotStatus
STATUS_MAP: dict[str, str] = {
    "free": "free",
    "full": "booked",
    "fullsell": "for_sale",
}

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "TennisCourtFinder/0.1",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://book.sebarena.lt",
    "Referer": "https://book.sebarena.lt/",
}
