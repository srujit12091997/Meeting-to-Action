"""Email integration: send the meeting summary via SMTP (e.g. Gmail).

Gmail setup: enable 2FA, create an App Password, and put it in .env as
SMTP_PASSWORD (SMTP_USER = your gmail address). Stdlib only — no extra deps.
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings


class EmailNotConfigured(RuntimeError):
    """Raised when SMTP credentials aren't set in .env."""


def send_summary_email(recipients: list[str], subject: str, html_body: str) -> int:
    """Send an HTML email to recipients. Returns how many it went to."""
    settings = get_settings()
    if not (settings.smtp_user and settings.smtp_password):
        raise EmailNotConfigured(
            "SMTP not configured. Set SMTP_USER and SMTP_PASSWORD (Gmail App "
            "Password) in .env to send email."
        )
    recipients = [r.strip() for r in recipients if r.strip()]
    if not recipients:
        raise ValueError("No recipients provided.")

    sender = settings.email_from or settings.smtp_user
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(sender, recipients, msg.as_string())
    return len(recipients)
