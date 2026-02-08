from __future__ import annotations

from uuid import UUID

BASE_URL = "https://www.tenisoerdve.lt"
CALENDAR_URL = (
    f"{BASE_URL}/erp/wkm/modules/TKCalendar/ajax/drawCalendar.php"
)

CLUB_ID = "teniso-erdve"
CLUB_UUID_NS = UUID("30000000-0000-0000-0000-0000000e7d00")
CLUB_NAME = "Teniso Erdvė"
CLUB_ADDRESS = "Žirgų g. 1, Gineitiškės, Vilniaus r."
CLUB_CITY = "Vilnius"
CLUB_PHONE = None
CLUB_WEBSITE = "https://www.tenisoerdve.lt/rezervacijos"

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (compatible; TennisCourtFinder/0.1)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lt,en;q=0.5",
}

# Place types used in the AJAX endpoint
PLACE_CLOSED = "closed"  # Indoor courts
PLACE_OPEN = "open"  # Outdoor courts

# Court type / surface mappings per place
PLACE_MAPPINGS: dict[str, dict[str, str]] = {
    PLACE_CLOSED: {
        "court_type": "indoor",
        "surface_type": "hard",
    },
    PLACE_OPEN: {
        "court_type": "outdoor",
        "surface_type": "hard",
    },
}

SLOT_DURATION_MINUTES = 30
