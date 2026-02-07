"""Tests for the /api/notifications endpoints."""

from uuid import uuid4


class TestNotificationsCRUD:
    def _create_subscription(self, client) -> dict:
        """Helper: create a subscription and return the JSON response."""
        resp = client.post(
            "/api/notifications",
            json={
                "club_id": "test-club",
                "notify_on_statuses": ["free"],
                "is_recurring": False,
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_create_subscription(self, client):
        data = self._create_subscription(client)
        assert data["club_id"] == "test-club"
        assert data["active"] is True
        assert data["is_recurring"] is False
        assert "id" in data

    def test_list_subscriptions_empty(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        # Note: may have leftover items from other tests in same process,
        # but the structure should be correct
        data = resp.json()
        assert "items" in data
        assert "meta" in data

    def test_get_subscription(self, client):
        created = self._create_subscription(client)
        sub_id = created["id"]

        resp = client.get(f"/api/notifications/{sub_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sub_id

    def test_get_nonexistent_subscription(self, client):
        fake_id = str(uuid4())
        resp = client.get(f"/api/notifications/{fake_id}")
        assert resp.status_code == 404

    def test_update_subscription(self, client):
        created = self._create_subscription(client)
        sub_id = created["id"]

        resp = client.put(
            f"/api/notifications/{sub_id}",
            json={
                "club_id": "test-club",
                "notify_on_statuses": ["free", "for_sale"],
                "is_recurring": True,
                "days_of_week": ["monday", "wednesday"],
                "time_from": "18:00",
                "time_to": "20:00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_recurring"] is True
        assert data["notify_on_statuses"] == ["free", "for_sale"]
        assert data["days_of_week"] == ["monday", "wednesday"]

    def test_toggle_subscription(self, client):
        created = self._create_subscription(client)
        sub_id = created["id"]

        # Deactivate
        resp = client.patch(
            f"/api/notifications/{sub_id}/toggle",
            json={"active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

        # Re-activate
        resp = client.patch(
            f"/api/notifications/{sub_id}/toggle",
            json={"active": True},
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is True

    def test_delete_subscription(self, client):
        created = self._create_subscription(client)
        sub_id = created["id"]

        resp = client.delete(f"/api/notifications/{sub_id}")
        assert resp.status_code == 204

        # Should be gone
        resp = client.get(f"/api/notifications/{sub_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent(self, client):
        fake_id = str(uuid4())
        resp = client.delete(f"/api/notifications/{fake_id}")
        assert resp.status_code == 404


class TestNotificationsAuth:
    def test_list_requires_auth(self, unauthed_client):
        resp = unauthed_client.get("/api/notifications")
        assert resp.status_code == 401

    def test_create_requires_auth(self, unauthed_client):
        resp = unauthed_client.post(
            "/api/notifications",
            json={
                "club_id": "test-club",
                "notify_on_statuses": ["free"],
                "is_recurring": False,
            },
        )
        assert resp.status_code == 401


class TestNotificationLogs:
    def test_list_logs_empty(self, client):
        # Create a subscription first
        resp = client.post(
            "/api/notifications",
            json={
                "club_id": "test-club",
                "notify_on_statuses": ["free"],
                "is_recurring": False,
            },
        )
        sub_id = resp.json()["id"]

        resp = client.get(f"/api/notifications/{sub_id}/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["meta"]["total_items"] == 0

    def test_list_logs_not_found(self, client):
        fake_id = str(uuid4())
        resp = client.get(f"/api/notifications/{fake_id}/logs")
        assert resp.status_code == 404
