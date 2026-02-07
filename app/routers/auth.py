"""
Authentication endpoints – email OTP flow (mocked).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Response

from app.dependencies import CurrentUser
from app.generated.models import (
    AuthResponse,
    MessageResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    UserInfo,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Mock OTP store (replace with real implementation) ─────────────────────
_MOCK_VALID_OTP = "123456"


@router.post(
    "/request-otp",
    response_model=OtpRequestResponse,
    operation_id="requestOtp",
    summary="Request a one-time password sent to the given email",
)
async def request_otp(body: OtpRequest) -> OtpRequestResponse:
    """
    Mock implementation: always returns success.
    In production this would send a real email with a time-limited OTP.
    """
    # TODO: Send actual OTP email
    return OtpRequestResponse(
        message=f"OTP sent to {body.email}",
        expires_in_seconds=300,
    )


@router.post(
    "/verify-otp",
    response_model=AuthResponse,
    operation_id="verifyOtp",
    summary="Verify OTP and receive a JWT session cookie",
)
async def verify_otp(body: OtpVerifyRequest, response: Response) -> AuthResponse:
    """
    Mock implementation: accepts OTP '123456' for any email.
    In production this would validate the OTP, create/find the user,
    generate a real JWT and set it in an HTTP-only cookie.
    """
    # TODO: Validate OTP and generate real JWT
    if body.otp_code != _MOCK_VALID_OTP:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    # Set mock JWT cookie
    mock_jwt = f"mock-jwt-for-{body.email}"
    response.set_cookie(
        key="session",
        value=mock_jwt,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
    )

    user = UserInfo(
        email=body.email,
        created_at=datetime.now(timezone.utc),
    )
    return AuthResponse(
        message="Authenticated successfully",
        user=user,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    operation_id="logout",
    summary="Clear the session cookie",
)
async def logout(current_user: CurrentUser, response: Response) -> MessageResponse:
    response.delete_cookie("session")
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserInfo,
    operation_id="getMe",
    summary="Get current authenticated user info",
)
async def get_me(current_user: CurrentUser) -> UserInfo:
    return current_user
