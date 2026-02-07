"""
Shared FastAPI dependencies – authentication, pagination, etc.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Query, status

from app.generated.models import UserInfo


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


# ── Authentication (mock) ─────────────────────────────────────────────────

# TODO: Replace with real JWT validation once auth is implemented.
# For now we parse the email out of the mock session cookie
# ("mock-jwt-for-{email}") so each login gets its own subscriptions.

_MOCK_COOKIE_PREFIX = "mock-jwt-for-"


async def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
) -> UserInfo:
    """
    Extract and validate the JWT from the session cookie.

    Currently a **mock** – the email is parsed from the cookie value.
    Replace with real JWT decoding later.
    """
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in via /api/auth/verify-otp",
        )

    # Extract email from "mock-jwt-for-{email}"
    if session.startswith(_MOCK_COOKIE_PREFIX):
        email = session[len(_MOCK_COOKIE_PREFIX):]
    else:
        email = "player@example.com"

    return UserInfo(
        email=email,
        created_at=datetime.now(timezone.utc),
    )


# Type alias for use as a dependency
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
