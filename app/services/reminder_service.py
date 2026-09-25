from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.db import store
from app.schemas import ReminderCreate, ReminderRead
from app.services.email_service import email_service


class ReminderService:
    def __init__(self) -> None:
        self.repo = store

    def create_reminder(self, payload: ReminderCreate) -> ReminderRead:
        user = self.repo.get_user_by_email(payload.user_email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        reminder = self.repo.create_reminder(payload)
        return ReminderRead(**reminder)

    def process_due_reminders(self) -> int:
        now = datetime.now(timezone.utc)
        due_reminders = self.repo.list_due_reminders(now)

        processed = 0
        for reminder in due_reminders:
            user = self.repo.get_user_by_email(reminder["user_email"])
            if user is None:
                self.repo.mark_reminder_sent(reminder["id"])
                continue

            email_service.send_reminder_email(
                to=user["email"],
                subject=reminder["title"],
                message=reminder["message"],
                name=user["name"],
            )
            self.repo.mark_reminder_sent(reminder["id"])
            processed += 1

        return processed


reminder_service = ReminderService()
