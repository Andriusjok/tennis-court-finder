import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException, Query, Response, status

from app.config import ENVIRONMENT, JWT_ALGORITHM, JWT_EXPIRY_DAYS, JWT_SECRET
from app.generated.models import PaginationMeta, UserInfo

logger = logging.getLogger(__name__)


# ── Pagination ─────────────────────────────────────────────────────────────


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
        page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(items: list, pagination: PaginationParams, response_cls: type):
    total = len(items)
    start = pagination.offset
    end = start + pagination.page_size
    return response_cls(
        items=items[start:end],
        meta=PaginationMeta(
            page=pagination.page,
            page_size=pagination.page_size,
            total_items=total,
            total_pages=max(1, -(-total // pagination.page_size)),
        ),
    )


# ── JWT / Session ──────────────────────────────────────────────────────────


def create_jwt(email: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": email,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_session_cookie(response: Response, email: str) -> None:
    token = create_jwt(email)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=ENVIRONMENT == "production",
        max_age=JWT_EXPIRY_DAYS * 86400,
    )


def decode_session_email(session: str | None) -> str | None:
    if not session:
        return None
    try:
        payload = jwt.decode(session, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


async def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
) -> UserInfo:
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
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session. Please log in again.",
        ) from None

    email: str | None = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    return UserInfo(
        email=email,
        created_at=datetime.fromtimestamp(payload.get("iat", 0), tz=UTC),
    )


CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
