"""
Authentication endpoints – email OTP flow with real JWT tokens.
"""

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.config import ENVIRONMENT, JWT_ALGORITHM, JWT_EXPIRY_DAYS, JWT_SECRET
from app.dependencies import CurrentUser
from app.generated.models import (
    AuthResponse,
    MessageResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    UserInfo,
)
from app import db
from app.rate_limit import STRICT, AUTH, limiter
from app.services.email import send_otp_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_jwt(email: str) -> str:
    """Create a signed JWT for the given email."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@router.post(
    "/request-otp",
    response_model=OtpRequestResponse,
    operation_id="requestOtp",
    summary="Request a one-time password sent to the given email",
)
@limiter.limit(STRICT)
async def request_otp(request: Request, body: OtpRequest) -> OtpRequestResponse:
    """
    Generate a 6-digit OTP, store it in the database, and send it via email.
    In dev mode (no SMTP configured), the OTP is printed to the console.
    """
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
    """
    Validate the OTP against the database. On success, generate a signed JWT,
    set it as an HTTP-only cookie, and return the user info.
    """
    valid = await db.verify_otp(body.email, body.otp_code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    token = _create_jwt(body.email)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=ENVIRONMENT == "production",
        max_age=JWT_EXPIRY_DAYS * 86400,
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
