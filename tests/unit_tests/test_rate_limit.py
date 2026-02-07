"""Tests for rate limiting behaviour."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from tests.mocks.models import MOCK_USER


class TestRateLimiting:
    """Verify that rate limiting kicks in for sensitive endpoints."""

    @pytest.fixture()
    def limited_client(self, _test_env):
        """
        TestClient with rate limiting **enabled** (unlike the default
        `client` fixture which disables it for convenience).
        """
        from app.rate_limit import limiter

        limiter.enabled = True
        # Reset in-memory state so previous tests don't pollute counts
        limiter.reset()

        async def _mock_current_user():
            return MOCK_USER

        app.dependency_overrides[get_current_user] = _mock_current_user

        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc

        app.dependency_overrides.clear()
        limiter.enabled = False

    def test_otp_request_rate_limit(self, limited_client):
        """POST /api/auth/request-otp is limited to 5 requests/minute."""
        for i in range(5):
            resp = limited_client.post(
                "/api/auth/request-otp",
                json={"email": "test@example.com"},
            )
            assert resp.status_code == 200, f"Request {i + 1} should succeed"

        # 6th request should be rate-limited
        resp = limited_client.post(
            "/api/auth/request-otp",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]

    def test_otp_verify_rate_limit(self, limited_client):
        """POST /api/auth/verify-otp is limited to 10 requests/minute."""
        for i in range(10):
            resp = limited_client.post(
                "/api/auth/verify-otp",
                json={"email": "test@example.com", "otp_code": "000000"},
            )
            # 401 (wrong OTP) is fine – we just need it not to be 429 yet
            assert resp.status_code in (200, 401), f"Request {i + 1} should not be rate-limited"

        # 11th request should be rate-limited
        resp = limited_client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "000000"},
        )
        assert resp.status_code == 429

    def test_general_endpoint_not_limited_at_low_volume(self, limited_client):
        """GET /api/clubs at low volume should not be rate-limited."""
        for _ in range(10):
            resp = limited_client.get("/api/clubs")
            assert resp.status_code == 200
