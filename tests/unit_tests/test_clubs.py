"""Tests for the /api/clubs endpoints."""

from tests.mocks.models import MOCK_CLUB, MOCK_CLUB_2


class TestListClubs:
    def test_list_all_clubs(self, client):
        resp = client.get("/api/clubs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        slugs = {c["id"] for c in data["items"]}
        assert "test-club" in slugs
        assert "other-club" in slugs

    def test_list_clubs_filter_by_city(self, client):
        resp = client.get("/api/clubs", params={"city": "Vilnius"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["city"] == "Vilnius"

    def test_list_clubs_filter_no_match(self, client):
        resp = client.get("/api/clubs", params={"city": "Klaipeda"})
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 0

    def test_list_clubs_pagination(self, client):
        resp = client.get("/api/clubs", params={"page": 1, "page_size": 1})
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["meta"]["total_items"] == 2
        assert data["meta"]["total_pages"] == 2


class TestGetClub:
    def test_get_existing_club(self, client):
        resp = client.get("/api/clubs/test-club")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "test-club"
        assert data["name"] == MOCK_CLUB.name

    def test_get_nonexistent_club(self, client):
        resp = client.get("/api/clubs/no-such-club")
        assert resp.status_code == 404
