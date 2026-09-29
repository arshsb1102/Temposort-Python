from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx

from app.core.environment import settings
from app.services.telemetry import EMAIL_DELIVERIES

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class RetryableEmailDeliveryError(EmailDeliveryError):
    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class PermanentEmailDeliveryError(EmailDeliveryError):
    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)


def send_via_smtp(to_email: str, subject: str, html_body: str) -> dict[str, Any]:
    if not settings.smtp_host:
        return {"provider": "smtp", "to": to_email, "subject": subject, "status": "failed", "retryable": False, "message": "SMTP host not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content("Please view this email in an HTML-capable client.")
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.ehlo()
            if settings.enable_ssl or settings.smtp_port == 587:
                server.starttls()
                server.ehlo()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            server.send_message(message)
        return {"provider": "smtp", "to": to_email, "subject": subject, "status": "sent"}
    except smtplib.SMTPResponseException as exc:
        logger.exception("SMTP delivery failed")
        return {
            "provider": "smtp",
            "to": to_email,
            "subject": subject,
            "status": "failed",
            "error": str(exc),
            "retryable": 400 <= exc.smtp_code < 500,
            "message": "SMTP delivery failed; message was not sent",
        }
    except (TimeoutError, OSError, smtplib.SMTPServerDisconnected) as exc:
        logger.exception("SMTP transport failed")
        return {
            "provider": "smtp",
            "to": to_email,
            "subject": subject,
            "status": "failed",
            "error": str(exc),
            "retryable": True,
            "message": "SMTP delivery failed; message was not sent",
        }
    except Exception as exc:  # pragma: no cover - defensive provider boundary
        logger.exception("Unexpected SMTP delivery failure")
        return {
            "provider": "smtp",
            "to": to_email,
            "subject": subject,
            "status": "failed",
            "error": str(exc),
            "retryable": False,
            "message": "SMTP delivery failed; message was not sent",
        }


def send_via_resend(
    to_email: str,
    subject: str,
    html_body: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    resend_api_key = settings.resend_api_key.get_secret_value()
    if not resend_api_key:
        return {"provider": "resend", "to": to_email, "subject": subject, "status": "failed", "retryable": False, "message": "RESEND_API_KEY not configured"}

    response = None
    try:
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        response = httpx.post(
            "https://api.resend.com/emails",
            headers=headers,
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
    except httpx.HTTPError as exc:
        body = response.text if response is not None else ""
        status_code = response.status_code if response is not None else None
        retryable = status_code is None or status_code == 429 or status_code >= 500
        logger.exception("Resend delivery failed")
        return {
            "provider": "resend",
            "to": to_email,
            "subject": subject,
            "status": "failed",
            "error": str(exc),
            "api_response": body,
            "retryable": retryable,
            "message": "Resend delivery failed; message was not sent",
        }


def send_email_message(
    to_email: str,
    subject: str,
    html_body: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    provider = settings.mail_provider.lower()
    if provider == "resend":
        result = send_via_resend(to_email, subject, html_body, idempotency_key)
    elif provider == "smtp":
        result = send_via_smtp(to_email, subject, html_body)
    else:
        result = {
            "provider": provider,
            "to": to_email,
            "subject": subject,
            "status": "failed",
            "retryable": False,
            "message": "MAIL_PROVIDER must be configured for delivery",
        }
    EMAIL_DELIVERIES.labels(provider, result["status"]).inc()
    return result
