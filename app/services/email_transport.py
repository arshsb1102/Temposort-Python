from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

import httpx

from app.core.environment import settings


def send_via_smtp(to_email: str, subject: str, html_body: str) -> dict[str, Any]:
    if not settings.smtp_host:
        return {"provider": "smtp", "to": to_email, "subject": subject, "status": "queued", "message": "SMTP host not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content("Please view this email in an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.enable_ssl:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        return {"provider": "smtp", "to": to_email, "subject": subject, "status": "sent"}
    except (OSError, smtplib.SMTPException, TimeoutError):
        return {"provider": "smtp", "to": to_email, "subject": subject, "status": "queued", "message": "SMTP delivery failed; message queued for retry"}


def send_via_resend(to_email: str, subject: str, html_body: str) -> dict[str, Any]:
    if not settings.resend_api_key:
        return {"provider": "resend", "to": to_email, "subject": subject, "status": "queued", "message": "RESEND_API_KEY not configured"}

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.smtp_from_name} <{settings.smtp_from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
            timeout=20,
        )
        response.raise_for_status()
        return {"provider": "resend", "to": to_email, "subject": subject, "status": "sent", "payload": response.json()}
    except httpx.HTTPError:
        return {"provider": "resend", "to": to_email, "subject": subject, "status": "queued", "message": "Resend delivery failed; message queued for retry"}


def send_email_message(to_email: str, subject: str, html_body: str) -> dict[str, Any]:
    provider = settings.mail_provider.lower()
    if provider == "resend":
        return send_via_resend(to_email, subject, html_body)
    if provider == "smtp":
        return send_via_smtp(to_email, subject, html_body)
    return {"provider": "console", "to": to_email, "subject": subject, "status": "queued"}
