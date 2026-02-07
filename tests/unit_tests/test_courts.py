"""Tests for the /api/clubs/{club_id}/courts endpoints."""

from tests.mocks.models import MOCK_COURT_HARD_INDOOR, MOCK_COURTS


class TestListCourts:
    def test_list_all_courts(self, client):
        resp = client.get("/api/clubs/test-club/courts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == len(MOCK_COURTS)

    def test_list_courts_filter_surface(self, client):
        resp = client.get("/api/clubs/test-club/courts", params={"surface_type": "clay"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["surface_type"] == "clay"

    def test_list_courts_filter_court_type(self, client):
        resp = client.get("/api/clubs/test-club/courts", params={"court_type": "indoor"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(c["court_type"] == "indoor" for c in data)

    def test_list_courts_unknown_club(self, client):
        resp = client.get("/api/clubs/no-such-club/courts")
        assert resp.status_code == 404


class TestGetCourt:
    def test_get_existing_court(self, client):
        court_id = str(MOCK_COURT_HARD_INDOOR.id)
        resp = client.get(f"/api/clubs/test-club/courts/{court_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Court 1"
        assert data["surface_type"] == "hard"

    def test_get_court_not_found(self, client):
        fake_id = "00000000-0000-0000-0000-000000000099"
        resp = client.get(f"/api/clubs/test-club/courts/{fake_id}")
        assert resp.status_code == 404

    def test_get_court_unknown_club(self, client):
        court_id = str(MOCK_COURT_HARD_INDOOR.id)
        resp = client.get(f"/api/clubs/no-such-club/courts/{court_id}")
        assert resp.status_code == 404
