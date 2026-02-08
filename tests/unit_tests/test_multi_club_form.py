"""Tests for multi-club notification form (UI + form-submission logic)."""

from __future__ import annotations

from app.dependencies import create_jwt
from tests.mocks.models import (
    MOCK_CLUB,
    MOCK_CLUB_2,
    MOCK_COURT_HARD_INDOOR,
    MOCK_COURT_OTHER_1,
    MOCK_USER,
)


def _session_cookie() -> dict[str, str]:
    """Return a cookie dict with a valid JWT for the mock user."""
    token = create_jwt(MOCK_USER.email)
    return {"session": token}


class TestPartialClubCourts:
    """GET /partials/club-courts with multi-club support."""

    def test_empty_returns_nothing(self, client):
        resp = client.get("/partials/club-courts")
        assert resp.status_code == 200
        assert resp.text == ""

    def test_single_club(self, client):
        resp = client.get("/partials/club-courts", params={"club_ids": MOCK_CLUB.id})
        assert resp.status_code == 200
        assert "Court 1" in resp.text

    def test_multiple_clubs(self, client):
        resp = client.get(
            "/partials/club-courts",
            params={"club_ids": [MOCK_CLUB.id, MOCK_CLUB_2.id]},
        )
        assert resp.status_code == 200
        # Courts from both clubs present
        assert "Court 1" in resp.text  # from test-club
        assert "Court A" in resp.text  # from other-club
        # Club name headings present
        assert MOCK_CLUB.name in resp.text
        assert MOCK_CLUB_2.name in resp.text

    def test_unknown_club_ignored(self, client):
        resp = client.get(
            "/partials/club-courts",
            params={"club_ids": ["nonexistent"]},
        )
        assert resp.status_code == 200
        assert resp.text == ""


class TestNotificationFormGet:
    """GET /notifications/new returns the multi-club form."""

    def test_new_form_no_preselection(self, client):
        resp = client.get("/notifications/new")
        assert resp.status_code == 200
        assert "New" in resp.text
        # Should contain both clubs as checkbox options
        assert MOCK_CLUB.name in resp.text
        assert MOCK_CLUB_2.name in resp.text

    def test_new_form_with_preselected_clubs(self, client):
        resp = client.get(
            "/notifications/new",
            params={"club_ids": [MOCK_CLUB.id]},
        )
        assert resp.status_code == 200
        # Courts from preselected club should be rendered
        assert "Court 1" in resp.text


class TestCreateNotificationMultiClub:
    """POST /notifications/new creates one subscription per selected club."""

    def test_single_club_creates_one_sub(self, client):
        resp = client.post(
            "/notifications/new",
            data={
                "club_ids": MOCK_CLUB.id,
                "notify_on_statuses": "free",
                "is_recurring": "false",
            },
            cookies=_session_cookie(),
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Verify the subscription was created
        api_resp = client.get("/api/notifications")
        subs = api_resp.json()["items"]
        matching = [s for s in subs if s["club_id"] == MOCK_CLUB.id]
        assert len(matching) >= 1

    def test_multi_club_creates_multiple_subs(self, client):
        resp = client.post(
            "/notifications/new",
            data={
                "club_ids": [MOCK_CLUB.id, MOCK_CLUB_2.id],
                "notify_on_statuses": "free",
                "is_recurring": "true",
                "days_of_week": "monday",
            },
            cookies=_session_cookie(),
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Verify subscriptions were created for both clubs
        api_resp = client.get("/api/notifications")
        subs = api_resp.json()["items"]
        club_ids_in_subs = {s["club_id"] for s in subs}
        assert MOCK_CLUB.id in club_ids_in_subs
        assert MOCK_CLUB_2.id in club_ids_in_subs

    def test_court_ids_filtered_per_club(self, client):
        """Court IDs from both clubs are submitted, but each subscription
        should only get the court IDs that belong to its club."""
        court_id_club1 = str(MOCK_COURT_HARD_INDOOR.id)
        court_id_club2 = str(MOCK_COURT_OTHER_1.id)

        resp = client.post(
            "/notifications/new",
            data={
                "club_ids": [MOCK_CLUB.id, MOCK_CLUB_2.id],
                "notify_on_statuses": "free",
                "is_recurring": "false",
                "court_ids": [court_id_club1, court_id_club2],
            },
            cookies=_session_cookie(),
            follow_redirects=False,
        )
        assert resp.status_code == 303

        # Each subscription should only have its own club's courts
        api_resp = client.get("/api/notifications")
        subs = api_resp.json()["items"]

        sub_club1 = [s for s in subs if s["club_id"] == MOCK_CLUB.id]
        sub_club2 = [s for s in subs if s["club_id"] == MOCK_CLUB_2.id]

        assert len(sub_club1) >= 1
        assert len(sub_club2) >= 1

        # Club 1's subscription should only have club 1's court
        if sub_club1[-1]["court_ids"]:
            assert court_id_club1 in sub_club1[-1]["court_ids"]
            assert court_id_club2 not in sub_club1[-1]["court_ids"]

        # Club 2's subscription should only have club 2's court
        if sub_club2[-1]["court_ids"]:
            assert court_id_club2 in sub_club2[-1]["court_ids"]
            assert court_id_club1 not in sub_club2[-1]["court_ids"]

    def test_no_clubs_redirects(self, client):
        resp = client.post(
            "/notifications/new",
            data={
                "notify_on_statuses": "free",
                "is_recurring": "false",
            },
            cookies=_session_cookie(),
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/notifications/new" in resp.headers["location"]

    def test_unauthenticated_redirects_to_login(self, client):
        resp = client.post(
            "/notifications/new",
            data={
                "club_ids": MOCK_CLUB.id,
                "notify_on_statuses": "free",
                "is_recurring": "false",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]
