from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock

from app.services.baltic_tennis.client import BalticTennisClient, ParsedSchedule, ParsedSlot
from app.services.baltic_tennis.config import CLUB_ID, DEFAULT_COURT_TYPE, DEFAULT_SURFACE_TYPE
from app.services.baltic_tennis.service import BalticTennisService, _court_uuid

# ── Sample HTML fragments ────────────────────────────────────────────────────

SCHEDULE_HTML_MIXED = """
<html>
<body>
<div class="booking-table-wrapper">
  <div class="rbt-wrapper">
    <div class="rbt-scroller responsive-booking-table">
      <table class="rbt-table">
        <thead>
          <tr>
            <th class="rbt-sticky-col"><span class="field-label">Aikštelė</span></th>
            <th colspan=2>09:00</th>
            <th colspan=2>10:00</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td class="rbt-sticky-col"><span>Hard 1</span></td>
            <td class="kaire full booking-slot-na past" style="background-color: #6BC2CC">
              <a href="#" class="pop" data-court="1" data-place="1" data-time="09:00" data-perparduodamas="" title=""></a>
            </td>
            <td class="desine full booking-slot-na past" style="background-color: #6BC2CC">
              <a href="#" class="pop" data-court="1" data-place="1" data-time="09:30" data-perparduodamas="" title=""></a>
            </td>
            <td class="kaire" style="background-color: #ffffff">
              <a href="#" class="pop" data-court="1" data-place="1" data-time="10:00" data-perparduodamas="" title=""></a>
            </td>
            <td class="desine" style="background-color: #ffffff">
              <a href="#" class="pop" data-court="1" data-place="1" data-time="10:30" data-perparduodamas="" title=""></a>
            </td>
          </tr>
          <tr>
            <td class="rbt-sticky-col"><span>Hard 2</span></td>
            <td class="kaire full booking-slot-na past" style="background-color: #6BC2CC">
              <a href="#" class="pop" data-court="8" data-place="1" data-time="09:00" data-perparduodamas="" title=""></a>
            </td>
            <td class="desine" style="background-color: #ffffff">
              <a href="#" class="pop" data-court="8" data-place="1" data-time="09:30" data-perparduodamas="" title=""></a>
            </td>
            <td class="kaire full booking-slot-na" style="background-color: #6BC2CC">
              <a href="#" class="pop" data-court="8" data-place="1" data-time="10:00" data-perparduodamas="1" title=""></a>
            </td>
            <td class="desine" style="background-color: #ffffff">
              <a href="#" class="pop" data-court="8" data-place="1" data-time="10:30" data-perparduodamas="" title=""></a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div class="row booking-table-legend">
    <div class="col-12 col-lg-auto">
      <span class="legend-label">Vienos valandos kaina:</span>
      <div class="legend-item"><span style="background-color: #6BC2CC;"></span> 35 €</div>
    </div>
  </div>
</div>
</body>
</html>
"""

SCHEDULE_HTML_EMPTY = """
<html><body><p>No table here</p></body></html>
"""

SCHEDULE_HTML_ALL_BOOKED = """
<html>
<body>
<table class="rbt-table">
  <thead><tr><th class="rbt-sticky-col">Aikštelė</th><th colspan=2>17:00</th></tr></thead>
  <tbody>
    <tr>
      <td class="rbt-sticky-col"><span>Hard 1</span></td>
      <td class="kaire full booking-slot-na">
        <a href="#" data-court="1" data-place="1" data-time="17:00" data-perparduodamas=""></a>
      </td>
      <td class="desine full booking-slot-na">
        <a href="#" data-court="1" data-place="1" data-time="17:30" data-perparduodamas=""></a>
      </td>
    </tr>
  </tbody>
</table>
</body>
</html>
"""


# ── Client / parser tests ────────────────────────────────────────────────────


class TestBalticTennisClientParser:
    def setup_method(self):
        self.client = BalticTennisClient()

    def test_parse_mixed_statuses(self):
        result = self.client._parse_html(SCHEDULE_HTML_MIXED)

        assert len(result.courts) == 2
        assert (1, "Hard 1") in result.courts
        assert (8, "Hard 2") in result.courts

        assert len(result.slots) == 8
        statuses = {(s.court_id, s.time): s.status for s in result.slots}

        assert statuses[(1, "09:00")] == "booked"
        assert statuses[(1, "09:30")] == "booked"
        assert statuses[(1, "10:00")] == "free"
        assert statuses[(1, "10:30")] == "free"

        assert statuses[(8, "09:00")] == "booked"
        assert statuses[(8, "09:30")] == "free"
        # data-perparduodamas="1" → for_sale
        assert statuses[(8, "10:00")] == "for_sale"
        assert statuses[(8, "10:30")] == "free"

    def test_parse_extracts_price(self):
        result = self.client._parse_html(SCHEDULE_HTML_MIXED)
        assert result.price_eur == 35.0

    def test_parse_empty_html(self):
        result = self.client._parse_html(SCHEDULE_HTML_EMPTY)
        assert result.courts == []
        assert result.slots == []
        assert result.price_eur is None

    def test_parse_all_booked(self):
        result = self.client._parse_html(SCHEDULE_HTML_ALL_BOOKED)
        assert len(result.courts) == 1
        assert all(s.status == "booked" for s in result.slots)

    def test_court_names_preserved(self):
        result = self.client._parse_html(SCHEDULE_HTML_MIXED)
        names = {s.court_name for s in result.slots}
        assert names == {"Hard 1", "Hard 2"}


# ── Service tests ─────────────────────────────────────────────────────────────


def _make_parsed_schedule() -> ParsedSchedule:
    return ParsedSchedule(
        courts=[(1, "Hard 1"), (8, "Hard 2")],
        slots=[
            ParsedSlot(court_id=1, court_name="Hard 1", time="09:00", status="booked"),
            ParsedSlot(court_id=1, court_name="Hard 1", time="09:30", status="free"),
            ParsedSlot(court_id=8, court_name="Hard 2", time="09:00", status="free"),
            ParsedSlot(court_id=8, court_name="Hard 2", time="09:30", status="for_sale"),
        ],
        price_eur=35.0,
    )


class TestBalticTennisService:
    def setup_method(self):
        self.mock_client = AsyncMock(spec=BalticTennisClient)
        self.mock_client.fetch_schedule = AsyncMock(return_value=_make_parsed_schedule())
        self.service = BalticTennisService(self.mock_client)

    async def test_get_club(self):
        club = self.service.get_club()
        assert club.id == CLUB_ID
        assert club.name == "BSport Arena (Baltic Tennis)"
        assert club.city == "Vilnius"

    async def test_list_courts(self):
        courts = await self.service.list_courts()
        assert len(courts) == 2
        assert courts[0].name == "Hard 1"
        assert courts[1].name == "Hard 2"
        assert all(c.surface_type == DEFAULT_SURFACE_TYPE for c in courts)
        assert all(c.court_type == DEFAULT_COURT_TYPE for c in courts)
        assert all(c.club_id == CLUB_ID for c in courts)

    async def test_list_courts_filters_surface(self):
        courts = await self.service.list_courts(surface_type="clay")
        assert courts == []

    async def test_list_courts_filters_court_type(self):
        courts = await self.service.list_courts(court_type="outdoor")
        assert courts == []

    async def test_list_courts_matching_filter(self):
        courts = await self.service.list_courts(surface_type="hard", court_type="indoor")
        assert len(courts) == 2

    async def test_get_court(self):
        await self.service.list_courts()
        court = await self.service.get_court(str(_court_uuid(1)))
        assert court is not None
        assert court.name == "Hard 1"

    async def test_get_court_not_found(self):
        await self.service.list_courts()
        court = await self.service.get_court("00000000-0000-0000-0000-000000000000")
        assert court is None

    async def test_list_time_slots(self):
        today = date.today()
        slots = await self.service.list_time_slots(date_from=today, date_to=today)
        assert len(slots) == 4

        booked = [s for s in slots if s.status == "booked"]
        free = [s for s in slots if s.status == "free"]
        for_sale = [s for s in slots if s.status == "for_sale"]
        assert len(booked) == 1
        assert len(free) == 2
        assert len(for_sale) == 1

    async def test_list_time_slots_has_correct_fields(self):
        today = date.today()
        slots = await self.service.list_time_slots(date_from=today, date_to=today)
        slot = slots[0]
        assert slot.club_id == CLUB_ID
        assert slot.duration_minutes == 30
        assert slot.price == 35.0
        assert slot.currency == "EUR"
        assert slot.start_time.tzinfo is not None

    async def test_list_time_slots_filter_by_status(self):
        today = date.today()
        slots = await self.service.list_time_slots(date_from=today, date_to=today, status="free")
        assert len(slots) == 2
        assert all(s.status == "free" for s in slots)

    async def test_list_time_slots_filter_by_court_id(self):
        today = date.today()
        court_uuid = str(_court_uuid(1))
        slots = await self.service.list_time_slots(
            date_from=today, date_to=today, court_id=court_uuid
        )
        assert len(slots) == 2
        assert all(s.court_name == "Hard 1" for s in slots)

    async def test_list_time_slots_filter_by_surface_type_no_match(self):
        today = date.today()
        slots = await self.service.list_time_slots(
            date_from=today, date_to=today, surface_type="clay"
        )
        assert slots == []

    async def test_list_time_slots_multiple_days(self):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        slots = await self.service.list_time_slots(date_from=today, date_to=tomorrow)
        assert len(slots) == 8
        assert self.mock_client.fetch_schedule.call_count == 2

    async def test_list_time_slots_sorted(self):
        today = date.today()
        slots = await self.service.list_time_slots(date_from=today, date_to=today)
        times = [(s.start_time, s.court_name) for s in slots]
        assert times == sorted(times)

    async def test_courts_cache_populated_from_time_slots(self):
        """Calling list_time_slots before list_courts should still populate the court cache."""
        service = BalticTennisService(self.mock_client)
        today = date.today()
        await service.list_time_slots(date_from=today, date_to=today)
        # Courts should now be cached, so list_courts won't call fetch_schedule again
        call_count_before = self.mock_client.fetch_schedule.call_count
        courts = await service.list_courts()
        assert len(courts) == 2
        assert self.mock_client.fetch_schedule.call_count == call_count_before
