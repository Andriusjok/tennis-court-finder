"""Tests for the /api/clubs/{club_id}/time-slots endpoints."""

from datetime import date, timedelta

from tests.mocks.models import MOCK_COURT_HARD_INDOOR

_TODAY = date.today().isoformat()
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()


class TestListClubTimeSlots:
    def test_list_all_slots(self, client):
        resp = client.get(
            "/api/clubs/test-club/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["total_items"] >= 1

    def test_list_slots_filter_status(self, client):
        resp = client.get(
            "/api/clubs/test-club/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY, "status": "free"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for slot in data["items"]:
            assert slot["status"] == "free"

    def test_list_slots_filter_surface(self, client):
        resp = client.get(
            "/api/clubs/test-club/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY, "surface_type": "clay"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for slot in data["items"]:
            assert slot["surface_type"] == "clay"

    def test_list_slots_pagination(self, client):
        resp = client.get(
            "/api/clubs/test-club/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2

    def test_list_slots_unknown_club(self, client):
        resp = client.get(
            "/api/clubs/no-such-club/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY},
        )
        assert resp.status_code == 404

    def test_list_slots_empty_date_range(self, client):
        """Future date with no slots returns an empty list."""
        far_future = "2030-01-01"
        resp = client.get(
            "/api/clubs/test-club/time-slots",
            params={"date_from": far_future, "date_to": far_future},
        )
        assert resp.status_code == 200
        assert resp.json()["meta"]["total_items"] == 0


class TestListCourtTimeSlots:
    def test_list_court_slots(self, client):
        court_id = str(MOCK_COURT_HARD_INDOOR.id)
        resp = client.get(
            f"/api/clubs/test-club/courts/{court_id}/time-slots",
            params={"date_from": _TODAY, "date_to": _TODAY},
        )
        assert resp.status_code == 200
        data = resp.json()
        for slot in data["items"]:
            assert slot["court_id"] == court_id
