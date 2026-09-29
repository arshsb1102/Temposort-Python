from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.db import store
from app.db.repositories.user_repository import UserRepository
from app.schemas import ReminderCreate, ReminderRead
from app.services.email_service import email_service
from app.services.email_transport import PermanentEmailDeliveryError, RetryableEmailDeliveryError
from app.services.redis_service import redis_service


class ReminderService:
    def __init__(self) -> None:
        self.repo = store
        self.user_repo = UserRepository()

    async def _get_user(self, user_id: str) -> dict:
        user = await self.user_repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def list_reminders(self, user_id: str) -> list[ReminderRead]:
        user = await self._get_user(user_id)
        return await self.repo.reminders.list_reminders(user["email"])

    async def create_reminder(self, user_id: str, payload: ReminderCreate) -> ReminderRead:
        user = await self._get_user(user_id)
        if user["email"].lower() != str(payload.user_email).lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only create your own reminders")

        reminder = await self.repo.reminders.create_reminder(payload)
        return ReminderRead(**reminder)

    async def process_due_reminders(self, user_email: str | None = None) -> int:
        now = datetime.now(timezone.utc)
        due_reminders = await self.repo.reminders.list_due_reminders(now, user_email)

        processed = 0
        for reminder in due_reminders:
            reminder_id = reminder["id"]
            lock_key = f"reminder:send:{reminder_id}"
            lock_token = redis_service.acquire_lock(lock_key)
            if lock_token is None:
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
                    idempotency_key=f"reminder-{reminder_id}",
                )
                if delivery.get("delivery", {}).get("status") != "sent":
                    error_message = f"Failed to deliver reminder {reminder_id}"
                    if delivery.get("delivery", {}).get("retryable"):
                        raise RetryableEmailDeliveryError(error_message)
                    raise PermanentEmailDeliveryError(error_message)

                await self.repo.reminders.mark_reminder_sent(reminder_id)
                processed += 1
            finally:
                redis_service.release_lock(lock_key, lock_token)

        return processed

    async def enqueue_due_reminder_processing(self, user_id: str) -> str:
        user = await self._get_user(user_id)
        from app.services.tasks import process_due_reminders_task

        result = process_due_reminders_task.delay(user["email"])
        return result.id


reminder_service = ReminderService()
