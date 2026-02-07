from __future__ import annotations

import secrets
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Cookie, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.dependencies import create_session_cookie, decode_session_email
from app.rate_limit import AUTH, STRICT, limiter
from app.services.email import send_otp_email
from app.services.registry import registry

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["pages"], include_in_schema=False)

_SURFACE_TYPES = ["hard", "clay", "carpet", "grass", "artificial_grass"]
_COURT_TYPES = ["indoor", "outdoor"]


def _today() -> date:
    return date.today()


def _parse_date(raw: str | None) -> date:
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError:
            pass
    return _today()


def _build_time_rows(
    slots: list,
    courts: list,
) -> list[tuple[str, dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = OrderedDict()
    for slot in slots:
        time_label = slot.start_time.strftime("%H:%M")
        if time_label not in rows:
            rows[time_label] = {}
        rows[time_label][str(slot.court_id)] = slot
    return list(rows.items())


def _get_email(session: str | None) -> str | None:
    return decode_session_email(session)


def _parse_notification_form(
    club_id: str,
    notify_on_statuses: list[str],
    time_from: str | None,
    time_to: str | None,
    is_recurring: str,
    days_of_week: list[str] | None,
    specific_dates: str | None,
    court_ids: list[str] | None,
    surface_types: list[str] | None,
    court_types: list[str] | None,
) -> dict:
    parsed_dates = None
    if specific_dates:
        parsed_dates = [d.strip() for d in specific_dates.split(",") if d.strip()]

    club_name = None
    service = registry.get_service(club_id)
    if service:
        club_name = service.get_club().name

    return dict(
        club_id=club_id,
        club_name=club_name,
        notify_on_statuses=notify_on_statuses,
        is_recurring=is_recurring == "true",
        time_from=time_from or None,
        time_to=time_to or None,
        days_of_week=days_of_week,
        specific_dates=parsed_dates,
        court_ids=court_ids,
        surface_types=surface_types,
        court_types=court_types,
    )


async def _fetch_slot_grid(
    club_id: str,
    selected: date,
    surface_type: str | None = None,
    court_type: str | None = None,
) -> tuple[list, list, list[tuple[str, dict[str, Any]]]]:
    service = registry.get_service(club_id)
    if service is None:
        return [], [], []
    courts = await service.list_courts(surface_type=surface_type, court_type=court_type)
    slots = await service.list_time_slots(
        date_from=selected,
        date_to=selected,
        surface_type=surface_type,
        court_type=court_type,
    )
    return courts, slots, _build_time_rows(slots, courts)


# ── Pages ──────────────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    clubs = registry.list_clubs()
    enriched = []
    for club in clubs:
        svc = registry.get_service(club.id)
        if svc:
            courts = await svc.list_courts()
            club = club.model_copy(update={"courts_count": len(courts)})
        enriched.append(club)
    return templates.TemplateResponse(
        "pages/home.html",
        {"request": request, "clubs": enriched},
    )


@router.get("/clubs/{club_id}/schedule", response_class=HTMLResponse)
async def schedule(
    request: Request,
    club_id: str,
    date: str | None = Query(None, alias="date"),
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
):
    service = registry.get_service(club_id)
    if service is None:
        raise HTTPException(status_code=404, detail=f"Club {club_id} not found")

    club = service.get_club()
    selected = _parse_date(date)
    prev_date = (selected - timedelta(days=1)).isoformat()
    next_date = (selected + timedelta(days=1)).isoformat()

    courts, _slots, time_rows = await _fetch_slot_grid(
        club_id,
        selected,
        surface_type,
        court_type,
    )

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
            "filters": {"surface_type": surface_type, "court_type": court_type},
        },
    )


# ── HTMX Partials ─────────────────────────────────────────────────────────


@router.get("/partials/clubs/{club_id}/slots", response_class=HTMLResponse)
async def partial_slot_grid(
    request: Request,
    club_id: str,
    date: str | None = Query(None),
    surface_type: str | None = Query(None),
    court_type: str | None = Query(None),
):
    service = registry.get_service(club_id)
    if service is None:
        return HTMLResponse("<p>Club not found.</p>", status_code=404)

    selected = _parse_date(date)
    courts, _slots, time_rows = await _fetch_slot_grid(
        club_id,
        selected,
        surface_type,
        court_type,
    )
    return templates.TemplateResponse(
        "partials/slot_grid.html",
        {"request": request, "courts": courts, "time_rows": time_rows},
    )


@router.get("/partials/notifications", response_class=HTMLResponse)
async def partial_subscription_list(
    request: Request,
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return HTMLResponse(
            '<p class="text-muted">Please <a href="/login">log in</a> to see your alerts.</p>'
        )

    subs = await db.list_subscriptions(email)
    return templates.TemplateResponse(
        "partials/subscription_list.html",
        {"request": request, "subscriptions": subs},
    )


@router.get("/partials/club-courts", response_class=HTMLResponse)
async def partial_club_courts(
    request: Request,
    club_id: str = Query(""),
):
    if not club_id:
        return HTMLResponse("")

    service = registry.get_service(club_id)
    if service is None:
        return HTMLResponse('<p class="text-muted">Club not found.</p>')

    courts = await service.list_courts()
    return templates.TemplateResponse(
        "partials/court_picker.html",
        {"request": request, "courts": courts, "selected_court_ids": []},
    )


# ── Notification Pages ─────────────────────────────────────────────────────


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, session: str | None = Cookie(None)):
    return templates.TemplateResponse(
        "pages/notifications.html",
        {"request": request, "flash": None},
    )


@router.get("/notifications/new", response_class=HTMLResponse)
async def notification_form(
    request: Request,
    club_id: str | None = Query(None),
):
    clubs = registry.list_clubs()
    courts = []
    if club_id:
        service = registry.get_service(club_id)
        if service:
            courts = await service.list_courts()

    return templates.TemplateResponse(
        "pages/notification_form.html",
        {
            "request": request,
            "clubs": clubs,
            "courts": courts,
            "selected_club_id": club_id,
            "surface_types": _SURFACE_TYPES,
            "court_types": _COURT_TYPES,
            "editing": False,
            "sub": None,
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
    court_ids: list[str] | None = Form(None),
    surface_types: list[str] | None = Form(None),
    court_types: list[str] | None = Form(None),
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return RedirectResponse("/login", status_code=303)

    form = _parse_notification_form(
        club_id,
        notify_on_statuses,
        time_from,
        time_to,
        is_recurring,
        days_of_week,
        specific_dates,
        court_ids,
        surface_types,
        court_types,
    )
    await db.create_subscription(user_email=email, **form)
    return RedirectResponse("/notifications", status_code=303)


@router.get("/notifications/{notification_id}/edit", response_class=HTMLResponse)
async def edit_notification_form(
    request: Request,
    notification_id: str,
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return RedirectResponse("/login", status_code=303)

    sub = await db.get_subscription(notification_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    clubs = registry.list_clubs()
    courts = []
    service = registry.get_service(sub.club_id)
    if service:
        courts = await service.list_courts()

    return templates.TemplateResponse(
        "pages/notification_form.html",
        {
            "request": request,
            "clubs": clubs,
            "courts": courts,
            "selected_club_id": sub.club_id,
            "surface_types": _SURFACE_TYPES,
            "court_types": _COURT_TYPES,
            "editing": True,
            "sub": sub,
        },
    )


@router.post("/notifications/{notification_id}/edit")
async def update_notification_page(
    request: Request,
    notification_id: str,
    club_id: str = Form(...),
    notify_on_statuses: list[str] = Form(...),
    time_from: str | None = Form(None),
    time_to: str | None = Form(None),
    is_recurring: str = Form("false"),
    days_of_week: list[str] | None = Form(None),
    specific_dates: str | None = Form(None),
    court_ids: list[str] | None = Form(None),
    surface_types: list[str] | None = Form(None),
    court_types: list[str] | None = Form(None),
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return RedirectResponse("/login", status_code=303)

    existing = await db.get_subscription(notification_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    form = _parse_notification_form(
        club_id,
        notify_on_statuses,
        time_from,
        time_to,
        is_recurring,
        days_of_week,
        specific_dates,
        court_ids,
        surface_types,
        court_types,
    )
    form.pop("club_name", None)
    await db.update_subscription(notification_id, **form)
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/{notification_id}/toggle")
async def toggle_notification_page(
    request: Request,
    notification_id: str,
    active: str = Form("true"),
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return RedirectResponse("/login", status_code=303)

    await db.toggle_subscription(notification_id, active == "true")
    return RedirectResponse("/notifications", status_code=303)


@router.post("/notifications/{notification_id}/delete")
async def delete_notification_page(
    request: Request,
    notification_id: str,
    session: str | None = Cookie(None),
):
    email = _get_email(session)
    if not email:
        return RedirectResponse("/login", status_code=303)

    await db.delete_subscription(notification_id)
    return RedirectResponse("/notifications", status_code=303)


# ── Login Pages ────────────────────────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request, "step": "email", "flash": None},
    )


@router.post("/login", response_class=HTMLResponse)
@limiter.limit(STRICT)
async def login_submit_email(
    request: Request,
    email: str = Form(...),
):
    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    await db.create_otp(email, otp_code, ttl_seconds=300)
    await send_otp_email(email, otp_code)

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
@limiter.limit(AUTH)
async def login_verify_otp(
    request: Request,
    response: Response,
    email: str = Form(...),
    otp_code: str = Form(...),
):
    valid = await db.verify_otp(email, otp_code)
    if not valid:
        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "step": "otp",
                "email": email,
                "flash": {"type": "error", "message": "Invalid or expired code. Try again."},
            },
        )

    redirect = RedirectResponse("/notifications", status_code=303)
    create_session_cookie(redirect, email)
    return redirect
