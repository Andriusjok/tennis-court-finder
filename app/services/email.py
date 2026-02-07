"""
Email service — sends notification emails via SMTP.

In development (no SMTP configured), emails are printed to the console
so you can see what *would* be sent without configuring a mail server.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import (
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
    smtp_enabled,
)
from app.generated.models import TimeSlot

logger = logging.getLogger(__name__)


def _build_slot_summary(slot: TimeSlot) -> str:
    """One-line human-readable summary of a time slot."""
    day = slot.start_time.strftime("%a %d %b")
    time = f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}"
    price = f" · {slot.price} {slot.currency}" if slot.price else ""
    return f"{slot.court_name} · {day} {time}{price}"


def _build_html_body(
    club_name: str,
    slots: list[TimeSlot],
) -> str:
    """Build a simple HTML email body listing the matching slots."""
    rows = ""
    for s in slots:
        status_color = {"free": "#2ecc40", "for_sale": "#f39c12"}.get(s.status, "#999")
        rows += f"""
        <tr>
          <td>{s.court_name}</td>
          <td>{s.start_time.strftime('%a %d %b')}</td>
          <td>{s.start_time.strftime('%H:%M')}–{s.end_time.strftime('%H:%M')}</td>
          <td style="color:{status_color};font-weight:bold">{s.status.replace('_', ' ')}</td>
          <td>{f'{s.price} {s.currency}' if s.price else '–'}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family:sans-serif;color:#333">
      <h2>🎾 Court Alert — {club_name}</h2>
      <p>Slots matching your alert are now available:</p>
      <table border="0" cellpadding="6" cellspacing="0"
             style="border-collapse:collapse;border:1px solid #ddd">
        <thead style="background:#f5f5f5">
          <tr>
            <th align="left">Court</th>
            <th align="left">Date</th>
            <th align="left">Time</th>
            <th align="left">Status</th>
            <th align="left">Price</th>
          </tr>
        </thead>
        <tbody>{rows}
        </tbody>
      </table>
      <p style="margin-top:1em;font-size:0.9em;color:#888">
        You're receiving this because you set up an alert on Tennis Court Finder.
      </p>
    </body>
    </html>
    """


async def send_notification_email(
    to_email: str,
    club_name: str,
    matching_slots: list[TimeSlot],
) -> None:
    """
    Send (or log) a notification email about matching time slots.

    If SMTP is not configured, falls back to console output.
    """
    subject = f"🎾 {len(matching_slots)} court slot(s) available — {club_name}"
    html_body = _build_html_body(club_name, matching_slots)

    # ── Console fallback (dev mode) ───────────────────────────────────
    if not smtp_enabled():
        logger.info(
            "📧 [DEV] Would send email to %s:\n"
            "  Subject: %s\n"
            "  Slots:\n%s",
            to_email,
            subject,
            "\n".join(f"    • {_build_slot_summary(s)}" for s in matching_slots),
        )
        return

    # ── Real SMTP send ────────────────────────────────────────────────
    import aiosmtplib

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = to_email

    # Plain text fallback
    plain = f"Court slots available at {club_name}:\n\n"
    plain += "\n".join(f"• {_build_slot_summary(s)}" for s in matching_slots)
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=SMTP_USE_TLS,
        )
        logger.info("Email sent to %s (%d slots)", to_email, len(matching_slots))
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        raise
