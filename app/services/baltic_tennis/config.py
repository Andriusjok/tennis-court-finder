from __future__ import annotations

from uuid import UUID

BASE_URL = "https://savitarna.baltictennis.lt"
RESERVATION_URL = f"{BASE_URL}/reservation/short"

CLUB_ID = "baltic-tennis"
CLUB_UUID_NS = UUID("20000000-0000-0000-0000-000000b71c00")
CLUB_NAME = "BSport Arena (Baltic Tennis)"
CLUB_ADDRESS = "Telšių g. 17"
CLUB_CITY = "Vilnius"
CLUB_PHONE = "+370 620 99399"
CLUB_WEBSITE = "https://savitarna.baltictennis.lt/reservation/short"

TENNIS_PLACE_ID = 1

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (compatible; TennisCourtFinder/0.1)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lt,en;q=0.5",
}

# All BSport Arena tennis courts are indoor hard courts.
DEFAULT_SURFACE_TYPE = "hard"
DEFAULT_COURT_TYPE = "indoor"

SLOT_DURATION_MINUTES = 30
