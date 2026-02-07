"""Tests for the /api/auth endpoints."""


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
    def test_verify_valid_otp(self, client):
        resp = client.post(
            "/api/auth/verify-otp",
            json={"email": "test@example.com", "otp_code": "123456"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Authenticated successfully"
        assert data["user"]["email"] == "test@example.com"
        # Should set session cookie
        assert "session" in resp.cookies

    def test_verify_invalid_otp(self, client):
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
