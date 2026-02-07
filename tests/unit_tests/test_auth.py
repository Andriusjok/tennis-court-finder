"""Tests for the /api/auth endpoints."""

from app import db


class TestRequestOtp:
    def test_request_otp_success(self, client):
        resp = client.post("/api/auth/request-otp", json={"email": "test@example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert "OTP sent" in data["message"]
        assert data["expires_in_seconds"] > 0

    def test_request_otp_invalid_email(self, client):
        resp = client.post("/api/auth/request-otp", json={"email": "not-an-email"})
        assert resp.status_code == 422


class TestVerifyOtp:
    async def test_verify_valid_otp(self, client):
        # Seed a known OTP in the database
        await db.create_otp("test@example.com", "654321", ttl_seconds=300)

        resp = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "654321"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Authenticated successfully"
        assert data["user"]["email"] == "test@example.com"
        # Should set session cookie (now a real JWT)
        assert "session" in resp.cookies

    async def test_verify_invalid_otp(self, client):
        # Seed a known OTP but try a wrong code
        await db.create_otp("test@example.com", "654321", ttl_seconds=300)

        resp = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "000000"},
        )
        assert resp.status_code == 401

    def test_verify_otp_wrong_length(self, client):
        resp = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "12345"},
        )
        assert resp.status_code == 422

    async def test_otp_cannot_be_reused(self, client):
        """An OTP can only be used once."""
        await db.create_otp("test@example.com", "111222", ttl_seconds=300)

        # First use → success
        resp1 = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "111222"},
        )
        assert resp1.status_code == 200

        # Second use → fail
        resp2 = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "111222"},
        )
        assert resp2.status_code == 401


class TestLogout:
    def test_logout(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully"


class TestMe:
    def test_get_me_authenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "player@example.com"

    def test_get_me_unauthenticated(self, unauthed_client):
        resp = unauthed_client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_get_me_with_real_jwt(self, unauthed_client):
        """Full flow: request OTP → verify → call /me with JWT cookie."""
        await db.create_otp("real@example.com", "999888", ttl_seconds=300)

        # Verify OTP to get JWT
        resp = unauthed_client.post(
            "/api/auth/verify-otp",
            json={"email": "real@example.com", "otp_code": "999888"},
        )
        assert resp.status_code == 200
        assert "session" in resp.cookies

        # Use the JWT cookie to call /me
        resp = unauthed_client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "real@example.com"
