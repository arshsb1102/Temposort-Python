from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.db import store
from app.db.repositories.user_repository import UserRepository
from app.schemas import ReminderCreate, ReminderRead
from app.services.email_service import email_service
from app.services.redis_service import redis_service


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
            reminder_id = reminder["id"]
            lock_key = f"reminder:send:{reminder_id}"
            if not redis_service.acquire_lock(lock_key, ttl_seconds=60 * 60 * 24):
                continue

            try:
                user = await self.user_repo.get_user_by_email(reminder["user_email"])
                if user is None:
                    await self.repo.reminders.mark_reminder_sent(reminder_id)
                    continue

                delivery = email_service.send_reminder_email(
                    to=user["email"],
                    subject=reminder["title"],
                    message=reminder["message"],
                    name=user["name"],
                )
                if delivery.get("delivery", {}).get("status") == "failed":
                    raise RuntimeError(f"Failed to deliver reminder {reminder_id}")

                await self.repo.reminders.mark_reminder_sent(reminder_id)
                processed += 1
            finally:
                if redis_service.client.get(lock_key) is not None:
                    redis_service.release_lock(lock_key)

        return processed

    async def enqueue_due_reminder_processing(self) -> str | None:
        try:
            from app.services.celery_app import process_due_reminders_task

            result = process_due_reminders_task.delay()
            return result.id
        except Exception:
            return None


reminder_service = ReminderService()
