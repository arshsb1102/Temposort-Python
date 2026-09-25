from __future__ import annotations

from typing import Any

from app.db.repositories.reminder_repository import ReminderRepository
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.user_repository import UserRepository
from app.db.session import DatabaseSession
from app.schemas import ReminderCreate, ReminderRead, TaskCreate, TaskRead


class PostgresStore:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/temposort") -> None:
        self.database_url = database_url
        self.session = DatabaseSession(database_url)
        self.users = UserRepository(self.session)
        self.tasks = TaskRepository(self.session)
        self.reminders = ReminderRepository(self.session)

    def clear(self) -> None:
        with self.session.cursor() as cursor:
            cursor.execute("DELETE FROM verification_tokens")
            cursor.execute("DELETE FROM reminders")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM users")
        self.session.connection.commit()

    def close(self) -> None:
        self.session.close()

    def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        return self.users.create_user(name, email, password_hash)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users.get_user_by_email(email)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return self.users.get_user_by_id(user_id)

    def set_user_verified(self, email: str) -> dict[str, Any] | None:
        return self.users.set_user_verified(email)

    def create_verification_token(self, email: str, token: str) -> None:
        self.users.create_verification_token(email, token)

    def verify_email_token(self, token: str) -> str | None:
        return self.users.verify_email_token(token)

    def delete_user(self, email: str) -> bool:
        return self.users.delete_user(email)

    def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        return self.tasks.create_task(user_id, payload)

    def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        return self.tasks.list_tasks_for_user(user_id)

    def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        return self.tasks.get_task_for_user(user_id, task_id)

    def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        return self.tasks.update_task_for_user(user_id, task_id, payload)

    def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        return self.tasks.toggle_task_for_user(user_id, task_id)

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        return self.tasks.delete_task_for_user(user_id, task_id)

    def create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        return self.reminders.create_reminder(payload)

    def list_reminders(self) -> list[ReminderRead]:
        return self.reminders.list_reminders()

    def list_due_reminders(self, now: Any) -> list[dict[str, Any]]:
        return self.reminders.list_due_reminders(now)

    def mark_reminder_sent(self, reminder_id: str) -> None:
        self.reminders.mark_reminder_sent(reminder_id)

