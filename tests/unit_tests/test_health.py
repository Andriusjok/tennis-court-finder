"""Tests for the /api/health endpoint."""


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data
