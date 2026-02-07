"""
Server-rendered HTML pages using Jinja2 + HTMX.

These routes serve the browser UI.  All data is fetched from the internal
service layer (the same code the JSON API uses), so the HTML stays in sync
with the REST endpoints automatically.
"""

from __future__ import annotations

from datetime import date, timedelta
from collections import OrderedDict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Cookie, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.registry import registry

# ── Template engine ───────────────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["pages"], include_in_schema=False)


# ── Helpers ───────────────────────────────────────────────────────────────


def _today() -> date:
    return date.today()


def _parse_date(raw: str | None) -> date:
    """Parse a date string or return today."""
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return _today()


def _build_time_rows(
    slots: list, courts: list
) -> list[tuple[str, dict[str, Any]]]:
    """
    Pivot a flat list of time slots into rows keyed by time label,
    each containing a dict mapping court_id → slot.

    Returns a list of (time_label, {court_id: slot}) sorted by time.
    """
    rows: dict[str, dict[str, Any]] = OrderedDict()
    for slot in slots:
        time_label = slot.start_time.strftime("%H:%M")
        if time_label not in rows:
            rows[time_label] = {}
        rows[time_label][str(slot.court_id)] = slot
    return list(rows.items())


# ── Surface / court type options ──────────────────────────────────────────

_SURFACE_TYPES = ["hard", "clay", "carpet", "grass", "artificial_grass"]
_COURT_TYPES = ["indoor", "outdoor"]


# ══════════════════════════════════════════════════════════════════════════
#                               PAGES
# ══════════════════════════════════════════════════════════════════════════


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page – list all clubs."""
    clubs = registry.list_clubs()
    # Enrich with court counts
    enriched = []
    for club in clubs:
        svc = registry.get_service(club.id)
        if svc:
            courts = await svc.list_courts()
            club = club.model_copy(update={"courts_count": len(courts)})
        enriched.append(club)
    return templates.TemplateResponse(
        "pages/home.html", {"request": request, "clubs": enriched}
    )


@router.get("/clubs/{club_id}/schedule", response_class=HTMLResponse)
async def schedule(
    request: Request,
    club_id: str,
    date: str | None = Query(None, alias="date"),
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
):
    """Schedule grid for a club on a given day."""
    service = registry.get_service(club_id)
    if service is None:
        raise HTTPException(status_code=404, detail=f"Club {club_id} not found")

    club = service.get_club()
    selected = _parse_date(date)
    prev_date = (selected - timedelta(days=1)).isoformat()
    next_date = (selected + timedelta(days=1)).isoformat()

    # Fetch courts + slots for the selected day
    courts = await service.list_courts(
        surface_type=surface_type, court_type=court_type
    )
    slots = await service.list_time_slots(
        date_from=selected,
        date_to=selected,
        surface_type=surface_type,
        court_type=court_type,
    )
    time_rows = _build_time_rows(slots, courts)

    return templates.TemplateResponse(
        "pages/schedule.html",
        {
            "request": request,
            "club": club,
            "courts": courts,
            "time_rows": time_rows,
            "selected_date": selected.isoformat(),
            "prev_date": prev_date,
            "next_date": next_date,
            "surface_types": _SURFACE_TYPES,
            "court_types": _COURT_TYPES,
            "filters": {
                "surface_type": surface_type,
                "court_type": court_type,
            },
        },
    )


# ══════════════════════════════════════════════════════════════════════════
#                           HTMX PARTIALS
# ══════════════════════════════════════════════════════════════════════════


@router.get("/partials/clubs/{club_id}/slots", response_class=HTMLResponse)
async def partial_slot_grid(
    request: Request,
    club_id: str,
    date: str | None = Query(None),
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
):
    """Return just the slot grid partial (for HTMX swap)."""
    service = registry.get_service(club_id)
    if service is None:
        return HTMLResponse("<p>Club not found.</p>", status_code=404)

    selected = _parse_date(date)
    courts = await service.list_courts(
        surface_type=surface_type, court_type=court_type
    )
    slots = await service.list_time_slots(
        date_from=selected,
        date_to=selected,
        surface_type=surface_type,
        court_type=court_type,
    )
    time_rows = _build_time_rows(slots, courts)

    return templates.TemplateResponse(
        "partials/slot_grid.html",
        {"request": request, "courts": courts, "time_rows": time_rows},
    )


@router.get("/partials/notifications", response_class=HTMLResponse)
async def partial_subscription_list(
    request: Request,
    session: str | None = Cookie(None),
):
    """Return the subscriptions table partial (for HTMX swap)."""
    if not session:
        return HTMLResponse(
            '<p class="text-muted">Please <a href="/login">log in</a> to see your alerts.</p>'
        )

    # Import the in-memory mock store directly
    from app.routers.notifications import _MOCK_SUBSCRIPTIONS

    subs = list(_MOCK_SUBSCRIPTIONS.values())
    return templates.TemplateResponse(
        "partials/subscription_list.html",
        {"request": request, "subscriptions": subs},
    )


# ══════════════════════════════════════════════════════════════════════════
#                        NOTIFICATION PAGES
# ══════════════════════════════════════════════════════════════════════════


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, session: str | None = Cookie(None)):
    """My notifications page."""
    return templates.TemplateResponse(
        "pages/notifications.html",
        {"request": request, "flash": None},
    )


@router.get("/notifications/new", response_class=HTMLResponse)
async def notification_form(
    request: Request,
    club_id: str | None = Query(None),
):
    """New notification subscription form."""
    clubs = registry.list_clubs()
    return templates.TemplateResponse(
        "pages/notification_form.html",
        {
            "request": request,
            "clubs": clubs,
            "selected_club_id": club_id,
        },
    )


@router.post("/notifications/new")
async def create_notification_page(
    request: Request,
    response: Response,
    club_id: str = Form(...),
    notify_on_statuses: list[str] = Form(...),
    time_from: str | None = Form(None),
    time_to: str | None = Form(None),
    is_recurring: str = Form("false"),
    days_of_week: list[str] | None = Form(None),
    specific_dates: str | None = Form(None),
    session: str | None = Cookie(None),
):
    """Handle form submission: create a notification via the API."""
    if not session:
        return RedirectResponse("/login", status_code=303)

    from datetime import datetime, timezone
    from uuid import uuid4
    from app.generated.models import NotificationSubscription
    from app.routers.notifications import _MOCK_SUBSCRIPTIONS

    now = datetime.now(timezone.utc)

    # Parse specific dates
    parsed_dates = None
    if specific_dates:
        parsed_dates = [
            d.strip()
            for d in specific_dates.split(",")
            if d.strip()
        ]

    sub = NotificationSubscription(
        id=uuid4(),
        club_id=club_id,
        club_name=None,
        notify_on_statuses=notify_on_statuses,
        time_from=time_from if time_from else None,
        time_to=time_to if time_to else None,
        is_recurring=is_recurring == "true",
        days_of_week=days_of_week,
        specific_dates=parsed_dates,
        active=True,
        created_at=now,
        updated_at=now,
    )
    _MOCK_SUBSCRIPTIONS[sub.id] = sub

    return RedirectResponse("/notifications", status_code=303)


# ══════════════════════════════════════════════════════════════════════════
#                            LOGIN PAGES
# ══════════════════════════════════════════════════════════════════════════


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page – email entry step."""
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "step": "email", "flash": None},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit_email(
    request: Request,
    email: str = Form(...),
):
    """Handle email form → show OTP entry step."""
    # In a real app we'd call the /api/auth/request-otp endpoint here
    return templates.TemplateResponse(
        "pages/login.html",
        {
            "request": request,
            "step": "otp",
            "email": email,
            "flash": {"type": "success", "message": f"Code sent to {email}"},
        },
    )


@router.post("/login/verify")
async def login_verify_otp(
    request: Request,
    response: Response,
    email: str = Form(...),
    otp_code: str = Form(...),
):
    """Verify OTP and set session cookie, then redirect to notifications."""
    from app.routers.auth import _MOCK_VALID_OTP

    if otp_code != _MOCK_VALID_OTP:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "step": "otp",
                "email": email,
                "flash": {"type": "error", "message": "Invalid code. Try again."},
            },
        )

    # Set session cookie (mock JWT)
    redirect = RedirectResponse("/notifications", status_code=303)
    redirect.set_cookie(
        key="session",
        value=f"mock-jwt-for-{email}",
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return redirect
