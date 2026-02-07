import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status

from app import db
from app.dependencies import CurrentUser, create_session_cookie
from app.generated.models import (
    AuthResponse,
    MessageResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    UserInfo,
)
from app.rate_limit import AUTH, STRICT, limiter
from app.services.email import send_otp_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/request-otp",
    response_model=OtpRequestResponse,
    operation_id="requestOtp",
    summary="Request a one-time password sent to the given email",
)
@limiter.limit(STRICT)
async def request_otp(request: Request, body: OtpRequest) -> OtpRequestResponse:
    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    await db.create_otp(body.email, otp_code, ttl_seconds=300)
    await send_otp_email(body.email, otp_code)
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
@limiter.limit(AUTH)
async def verify_otp(request: Request, body: OtpVerifyRequest, response: Response) -> AuthResponse:
    valid = await db.verify_otp(body.email, body.otp_code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    create_session_cookie(response, body.email)

    user = UserInfo(email=body.email, created_at=datetime.now(UTC))
    return AuthResponse(message="Authenticated successfully", user=user)


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
