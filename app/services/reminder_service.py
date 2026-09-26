from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.db import store
from app.db.repositories.user_repository import UserRepository
from app.schemas import ReminderCreate, ReminderRead
from app.services.email_service import email_service


class ReminderService:
    def __init__(self) -> None:
        self.repo = store
        self.user_repo = UserRepository()

    async def list_reminders(self) -> list[ReminderRead]:
        return await self.repo.reminders.list_reminders()

    async def create_reminder(self, payload: ReminderCreate) -> ReminderRead:
        user = await self.user_repo.get_user_by_email(payload.user_email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        reminder = await self.repo.reminders.create_reminder(payload)
        return ReminderRead(**reminder)

    async def process_due_reminders(self) -> int:
        now = datetime.now(timezone.utc)
        due_reminders = await self.repo.reminders.list_due_reminders(now)

        processed = 0
        for reminder in due_reminders:
            user = await self.user_repo.get_user_by_email(reminder["user_email"])
            if user is None:
                await self.repo.reminders.mark_reminder_sent(reminder["id"])
                continue

            email_service.send_reminder_email(
                to=user["email"],
                subject=reminder["title"],
                message=reminder["message"],
                name=user["name"],
            )
            await self.repo.reminders.mark_reminder_sent(reminder["id"])
            processed += 1

        return processed


reminder_service = ReminderService()
