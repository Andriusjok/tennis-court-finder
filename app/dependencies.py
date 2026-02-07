"""
Shared FastAPI dependencies – authentication, pagination, etc.
"""

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
# For now, this is a mock that accepts any value in the "session" cookie
# and returns a fake user.

_MOCK_USER = UserInfo(
    email="player@example.com",
    created_at="2026-01-01T00:00:00Z",
)


async def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
) -> UserInfo:
    """
    Extract and validate the JWT from the session cookie.

    Currently a **mock** – any non-empty cookie value is accepted and a
    static test user is returned.  Replace with real JWT decoding later.
    """
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in via /api/auth/verify-otp",
        )
    # Mock: accept any token
    return _MOCK_USER


# Type alias for use as a dependency
CurrentUser = Annotated[UserInfo, Depends(get_current_user)]
