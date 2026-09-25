from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from app.schemas import ReminderCreate, ReminderRead, TaskCreate, TaskRead


class PostgresStore:
    def __init__(self, database_url: str = "postgresql://postgres:postgres@localhost:5432/temposort") -> None:
        self.database_url = database_url
        self.connection = psycopg.connect(database_url, autocommit=False)
        self._create_tables()

    @contextmanager
    def _cursor(self) -> Iterator[Any]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            yield cursor

    def _create_tables(self) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_at TIMESTAMPTZ,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    scheduled_for TIMESTAMPTZ NOT NULL,
                    sent_at TIMESTAMPTZ,
                    is_sent BOOLEAN NOT NULL DEFAULT FALSE
                );

                CREATE TABLE IF NOT EXISTS verification_tokens (
                    token TEXT PRIMARY KEY,
                    email TEXT NOT NULL
                );
                """
            )
        self.connection.commit()

    def _row_to_dict(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def _parse_datetime_value(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def clear(self) -> None:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM verification_tokens")
            cursor.execute("DELETE FROM reminders")
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM users")
        self.connection.commit()

    def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        email_key = email.lower()
        if self.get_user_by_email(email_key) is not None:
            raise ValueError("Email already registered.")

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (id, name, email, password_hash, is_verified, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, name, email_key, password_hash, False, now),
            )
        self.connection.commit()
        return self.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE lower(email) = lower(%s)", (email,))
            row = cursor.fetchone()
        return self._row_to_dict(row)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
        return self._row_to_dict(row)

    def set_user_verified(self, email: str) -> dict[str, Any] | None:
        with self._cursor() as cursor:
            cursor.execute("UPDATE users SET is_verified = TRUE WHERE lower(email) = lower(%s)", (email,))
        self.connection.commit()
        return self.get_user_by_email(email)

    def create_verification_token(self, email: str, token: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "INSERT INTO verification_tokens (token, email) VALUES (%s, %s)",
                (token, email.lower()),
            )
        self.connection.commit()

    def verify_email_token(self, token: str) -> str | None:
        with self._cursor() as cursor:
            cursor.execute("SELECT email FROM verification_tokens WHERE token = %s", (token,))
            row = cursor.fetchone()
            if row is None:
                return None
            email = row["email"]
            cursor.execute("DELETE FROM verification_tokens WHERE token = %s", (token,))
        self.connection.commit()
        return email

    def create_task(self, user_id: str, payload: TaskCreate) -> TaskRead:
        task_id = str(uuid4())
        now = datetime.now(timezone.utc)
        task = TaskRead(
            id=task_id,
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            priority=payload.priority,
            is_completed=False,
            created_at=now,
            updated_at=now,
        )
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (id, user_id, title, description, due_at, priority, is_completed, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    task.id,
                    user_id,
                    task.title,
                    task.description,
                    task.due_at,
                    task.priority,
                    task.is_completed,
                    task.created_at,
                    task.updated_at,
                ),
            )
        self.connection.commit()
        return task

    def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
            rows = cursor.fetchall()
        return [self._task_from_row(row) for row in rows]

    def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND id = %s", (user_id, task_id))
            row = cursor.fetchone()
        if row is None:
            return None
        return self._task_from_row(row)

    def _task_from_row(self, row: dict[str, Any]) -> TaskRead:
        return TaskRead(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            due_at=self._parse_datetime_value(row.get("due_at")),
            priority=row["priority"],
            is_completed=bool(row["is_completed"]),
            created_at=self._parse_datetime_value(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=self._parse_datetime_value(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def update_task_for_user(self, user_id: str, task_id: str, payload: TaskCreate) -> TaskRead:
        task = self.get_task_for_user(user_id, task_id)
        if task is None:
            raise ValueError("Task not found")

        updated = TaskRead(
            id=task.id,
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            priority=payload.priority,
            is_completed=task.is_completed,
            created_at=task.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE tasks
                SET title = %s, description = %s, due_at = %s, priority = %s, updated_at = %s
                WHERE user_id = %s AND id = %s
                """,
                (
                    updated.title,
                    updated.description,
                    updated.due_at,
                    updated.priority,
                    updated.updated_at,
                    user_id,
                    task_id,
                ),
            )
        self.connection.commit()
        return updated

    def toggle_task_for_user(self, user_id: str, task_id: str) -> TaskRead:
        task = self.get_task_for_user(user_id, task_id)
        if task is None:
            raise ValueError("Task not found")

        task.is_completed = not task.is_completed
        task.updated_at = datetime.now(timezone.utc)
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET is_completed = %s, updated_at = %s WHERE user_id = %s AND id = %s",
                (task.is_completed, task.updated_at, user_id, task_id),
            )
        self.connection.commit()
        return task

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        with self._cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE user_id = %s AND id = %s", (user_id, task_id))
            deleted = cursor.rowcount > 0
        self.connection.commit()
        return deleted

    def delete_user(self, email: str) -> bool:
        user = self.get_user_by_email(email)
        if user is None:
            return False

        with self._cursor() as cursor:
            cursor.execute("DELETE FROM verification_tokens WHERE lower(email) = lower(%s)", (email,))
            cursor.execute("DELETE FROM reminders WHERE lower(user_email) = lower(%s)", (email,))
            cursor.execute("DELETE FROM tasks WHERE user_id = %s", (user["id"],))
            cursor.execute("DELETE FROM users WHERE lower(email) = lower(%s)", (email,))
        self.connection.commit()
        return True

    def create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        reminder_id = str(uuid4())
        reminder = {
            "id": reminder_id,
            "user_email": payload.user_email.lower(),
            "title": payload.title,
            "message": payload.message,
            "channel": payload.channel,
            "scheduled_for": payload.scheduled_for,
            "sent_at": None,
            "is_sent": False,
        }
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reminders (id, user_email, title, message, channel, scheduled_for, sent_at, is_sent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    reminder["id"],
                    reminder["user_email"],
                    reminder["title"],
                    reminder["message"],
                    reminder["channel"],
                    reminder["scheduled_for"],
                    None,
                    False,
                ),
            )
        self.connection.commit()
        return reminder

    def list_reminders(self) -> list[ReminderRead]:
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM reminders ORDER BY scheduled_for ASC")
            rows = cursor.fetchall()
        reminders: list[ReminderRead] = []
        for row in rows:
            reminders.append(
                ReminderRead(
                    id=row["id"],
                    user_email=row["user_email"],
                    title=row["title"],
                    message=row["message"],
                    channel=row["channel"],
                    scheduled_for=self._parse_datetime_value(row["scheduled_for"]) or datetime.now(timezone.utc),
                    sent_at=self._parse_datetime_value(row.get("sent_at")),
                    is_sent=bool(row["is_sent"]),
                )
            )
        return reminders

    def list_due_reminders(self, now: datetime) -> list[dict[str, Any]]:
        with self._cursor() as cursor:
            cursor.execute(
                "SELECT * FROM reminders WHERE is_sent = FALSE AND scheduled_for <= %s ORDER BY scheduled_for ASC",
                (now,),
            )
            rows = cursor.fetchall()
        reminders: list[dict[str, Any]] = []
        for row in rows:
            reminders.append(
                {
                    "id": row["id"],
                    "user_email": row["user_email"],
                    "title": row["title"],
                    "message": row["message"],
                    "channel": row["channel"],
                    "scheduled_for": self._parse_datetime_value(row["scheduled_for"]) or now,
                    "sent_at": self._parse_datetime_value(row.get("sent_at")),
                    "is_sent": bool(row["is_sent"]),
                }
            )
        return reminders

    def mark_reminder_sent(self, reminder_id: str) -> None:
        with self._cursor() as cursor:
            cursor.execute(
                "UPDATE reminders SET sent_at = %s, is_sent = TRUE WHERE id = %s",
                (datetime.now(timezone.utc), reminder_id),
            )
        self.connection.commit()
