from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete

from app.db.base import AsyncSessionLocal
from app.db.models import Reminder, Task, User, VerificationToken
from app.db.repositories.reminder_repository import ReminderRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas import ReminderCreate, ReminderRead, TaskCreate, TaskRead


class PostgresStore:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/temposort") -> None:
        self.database_url = database_url
        self.users = UserRepository()
        self.tasks = TaskRepository()
        self.reminders = ReminderRepository()

    async def _clear_all(self) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(VerificationToken))
            await session.execute(delete(Reminder))
            await session.execute(delete(Task))
            await session.execute(delete(User))
            await session.commit()

    async def clear(self) -> None:
        await self._clear_all()

    async def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        return await self.users.create_user(name, email, password_hash)

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.users.get_user_by_email(email)

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await self.users.get_user_by_id(user_id)

    async def set_user_verified(self, email: str) -> dict[str, Any] | None:
        return await self.users.set_user_verified(email)

    async def create_verification_token(self, email: str, token: str) -> None:
        await self.users.create_verification_token(email, token)

    async def verify_email_token(self, token: str) -> str | None:
        return await self.users.verify_email_token(token)

    async def delete_user(self, email: str) -> bool:
        return await self.users.delete_user(email)

    async def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        return await self.tasks.create_task(user_id, payload)

    async def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        return await self.tasks.list_tasks_for_user(user_id)

    async def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        return await self.tasks.get_task_for_user(user_id, task_id)

    async def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        return await self.tasks.update_task_for_user(user_id, task_id, payload)

    async def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        return await self.tasks.toggle_task_for_user(user_id, task_id)

    async def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        return await self.tasks.delete_task_for_user(user_id, task_id)

    async def create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        return await self.reminders.create_reminder(payload)

    async def list_reminders(self, user_email: str) -> list[ReminderRead]:
        return await self.reminders.list_reminders(user_email)

    async def list_due_reminders(self, now: datetime, user_email: str | None = None) -> list[dict[str, Any]]:
        return await self.reminders.list_due_reminders(now, user_email)

    async def mark_reminder_sent(self, reminder_id: str) -> None:
        await self.reminders.mark_reminder_sent(reminder_id)

