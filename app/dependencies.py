"""
Shared FastAPI dependencies – authentication, pagination, etc.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Query, status

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.generated.models import UserInfo

logger = logging.getLogger(__name__)


# ── Pagination ────────────────────────────────────────────────────────────


class PaginationParams:
    """Common pagination query parameters."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        page_size: Annotated[
            int, Query(ge=1, le=100, description="Items per page")
        ] = 20,
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ── JWT helpers ───────────────────────────────────────────────────────────


def decode_session_email(session: str | None) -> str | None:
    """
    Decode the session JWT and return the email, or None if invalid/absent.

    This is a non-throwing helper for code paths that should degrade
    gracefully when the user is not logged in (e.g. page rendering).
    """
    if not session:
        return None
    try:
        payload = jwt.decode(session, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


# ── Authentication dependency ─────────────────────────────────────────────


async def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
) -> UserInfo:
    """
    Extract and validate the JWT from the session cookie.

    Raises 401 if the cookie is missing or the token is invalid/expired.
    """
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in via /api/auth/verify-otp",
        )

    try:
        payload = jwt.decode(session, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session. Please log in again.",
        )

    email: str | None = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    return UserInfo(
        email=email,
        created_at=datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc),
    )


# Type alias for use as a dependency
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
