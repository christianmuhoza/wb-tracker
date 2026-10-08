"""Minimal SMTP email delivery.

Used for password reset links. Sending is best-effort: failures are logged
and never allowed to break the requesting API endpoint. Email is optional —
when SMTP_HOST is unset the service reports itself as unavailable and the
admin-issued reset link flow remains the fallback.
"""

import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_STARTTLS, SMTP_USER, email_configured

log = logging.getLogger(__name__)

LOGO_PATH = Path(__file__).resolve().parent / "logo.png"


def send_email(to: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    """Send an email. Returns True on success, False otherwise (never raises)."""
    to = (to or "").strip()
    if not to:
        log.warning("send_email called without a recipient")
        return False
    if not email_configured():
        log.warning("Email not configured (SMTP_HOST/SMTP_FROM missing); skipping send to %s", to)
        return False

    # multipart/related so the logo can be embedded inline via cid:logo
    message = MIMEMultipart("related")
    message["Subject"] = subject
    message["From"] = SMTP_FROM or SMTP_USER
    message["To"] = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        alt.attach(MIMEText(html_body, "html", "utf-8"))
    message.attach(alt)

    try:
        logo_bytes = LOGO_PATH.read_bytes() if LOGO_PATH.exists() else None
    except OSError:
        logo_bytes = None
    if logo_bytes:
        image = MIMEImage(logo_bytes, _subtype="png")
        image.add_header("Content-ID", "<logo>")
        image.add_header("Content-Disposition", "inline", filename="logo.png")
        message.attach(image)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_STARTTLS:
                server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(message["From"], [to], message.as_string())
        log.info("Email sent to %s (%r)", to, subject)
        return True
    except Exception:
        log.exception("Failed to send email to %s", to)
        return False
