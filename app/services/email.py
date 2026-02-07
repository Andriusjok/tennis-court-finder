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


async def _send_email(to: str, subject: str, plain: str, html: str) -> None:
    import aiosmtplib

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            start_tls=SMTP_USE_TLS,
        )
        logger.info("Email sent to %s", to)
    except Exception:
        logger.exception("Failed to send email to %s", to)
        raise


def _slot_summary(slot: TimeSlot) -> str:
    day = slot.start_time.strftime("%a %d %b")
    time = f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}"
    price = f" · {slot.price} {slot.currency}" if slot.price else ""
    return f"{slot.court_name} · {day} {time}{price}"


def _notification_html(club_name: str, slots: list[TimeSlot]) -> str:
    rows = ""
    for s in slots:
        status_color = {"free": "#2ecc40", "for_sale": "#f39c12"}.get(s.status, "#999")
        rows += f"""
        <tr>
          <td>{s.court_name}</td>
          <td>{s.start_time.strftime("%a %d %b")}</td>
          <td>{s.start_time.strftime("%H:%M")}–{s.end_time.strftime("%H:%M")}</td>
          <td style="color:{status_color};font-weight:bold">{s.status.replace("_", " ")}</td>
          <td>{f"{s.price} {s.currency}" if s.price else "–"}</td>
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


async def send_otp_email(to_email: str, otp_code: str) -> None:
    subject = "🎾 Tennis Court Finder — Your login code"
    html = f"""
    <html>
    <body style="font-family:sans-serif;color:#333">
      <h2>🎾 Tennis Court Finder</h2>
      <p>Your one-time login code is:</p>
      <p style="font-size:2rem;font-weight:bold;letter-spacing:0.3em;
                color:#1a73e8;margin:1em 0">{otp_code}</p>
      <p>This code expires in 5 minutes.</p>
      <p style="margin-top:2em;font-size:0.9em;color:#888">
        If you didn't request this, you can safely ignore this email.
      </p>
    </body>
    </html>
    """
    plain = f"Your Tennis Court Finder login code is: {otp_code}\n\nExpires in 5 minutes."

    if not smtp_enabled():
        logger.info("📧 [DEV] OTP for %s: %s", to_email, otp_code)
        return

    await _send_email(to_email, subject, plain, html)


async def send_notification_email(
    to_email: str,
    club_name: str,
    matching_slots: list[TimeSlot],
) -> None:
    subject = f"🎾 {len(matching_slots)} court slot(s) available — {club_name}"
    html = _notification_html(club_name, matching_slots)
    plain = f"Court slots available at {club_name}:\n\n"
    plain += "\n".join(f"• {_slot_summary(s)}" for s in matching_slots)

    if not smtp_enabled():
        logger.info(
            "📧 [DEV] Would send to %s: %s\n%s",
            to_email,
            subject,
            "\n".join(f"    • {_slot_summary(s)}" for s in matching_slots),
        )
        return

    await _send_email(to_email, subject, plain, html)
