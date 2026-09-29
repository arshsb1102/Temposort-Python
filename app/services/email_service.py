from __future__ import annotations

from typing import Any

from app.core.environment import settings
from app.services.email_transport import send_email_message


class EmailService:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []

    def clear_history(self) -> None:
        self.sent_messages.clear()

    def send_email(self, to: str, subject: str, body: str, html: str | None = None, token: str | None = None) -> dict[str, Any]:
        payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "html": html,
            "token": token,
            "provider": settings.mail_provider,
        }
        self.sent_messages.append(payload)
        return payload

    def send_verification_email(self, to: str, name: str, token: str) -> dict[str, Any]:
        verification_url = f"{settings.api_base_url}/api/v1/auth/verify-email?token={token}"
        html = f"<p>Hi {name}</p><p><a href='{verification_url}'>Verify email</a></p>"
        body = (
            f"Hi {name}, please verify your TempoSort account by visiting: {verification_url}\n"
            "This verification link is valid for 24 hours."
        )
        result = send_email_message(to, "Verify your TempoSort email", html)
        payload = self.send_email(
            to=to,
            subject="Verify your TempoSort email",
            body=body,
            html=html,
            token=token,
        )
        payload["delivery"] = result
        return payload

    def send_reminder_email(
        self,
        to: str,
        subject: str,
        message: str,
        name: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        recipient_name = name or "there"
        html = f"<p>Hi {recipient_name},</p><p>{message}</p>"
        body = f"Hi {recipient_name},\n\n{message}"
        result = send_email_message(to, subject, html, idempotency_key)
        payload = self.send_email(to=to, subject=subject, body=body, html=html)
        payload["delivery"] = result
        return payload


email_service = EmailService()
