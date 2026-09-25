from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.schemas import ReminderCreate, ReminderRead, TaskCreate, TaskRead


class SQLiteStore:
    def __init__(self, database_url: str = "sqlite:///./temposort.db") -> None:
        self.database_url = database_url
        self.connection = sqlite3.connect("temposort.db", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_at TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                is_completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                channel TEXT NOT NULL,
                scheduled_for TEXT NOT NULL,
                sent_at TEXT,
                is_sent INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS verification_tokens (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def _parse_datetime_value(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)

    def clear(self) -> None:
        self.connection.execute("DELETE FROM verification_tokens")
        self.connection.execute("DELETE FROM reminders")
        self.connection.execute("DELETE FROM tasks")
        self.connection.execute("DELETE FROM users")
        self.connection.commit()

    def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        email_key = email.lower()
        if self.get_user_by_email(email_key) is not None:
            raise ValueError("Email already registered.")

        user_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """
            INSERT INTO users (id, name, email, password_hash, is_verified, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (user_id, name, email_key, password_hash, now),
        )
        self.connection.commit()
        return self.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)",
            (email,),
        ).fetchone()
        return self._row_to_dict(row)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._row_to_dict(row)

    def set_user_verified(self, email: str) -> dict[str, Any] | None:
        self.connection.execute(
            "UPDATE users SET is_verified = 1 WHERE lower(email) = lower(?)",
            (email,),
        )
        self.connection.commit()
        return self.get_user_by_email(email)

    def create_verification_token(self, email: str, token: str) -> None:
        self.connection.execute(
            "INSERT INTO verification_tokens (token, email) VALUES (?, ?)",
            (token, email.lower()),
        )
        self.connection.commit()

    def verify_email_token(self, token: str) -> str | None:
        row = self.connection.execute(
            "SELECT email FROM verification_tokens WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        email = row["email"]
        self.connection.execute("DELETE FROM verification_tokens WHERE token = ?", (token,))
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
        self.connection.execute(
            """
            INSERT INTO tasks (id, user_id, title, description, due_at, priority, is_completed, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                user_id,
                task.title,
                task.description,
                task.due_at.isoformat() if task.due_at else None,
                task.priority,
                int(task.is_completed),
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
            ),
        )
        self.connection.commit()
        return task

    def list_tasks_for_user(self, user_id: str) -> list[TaskRead]:
        rows = self.connection.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def get_task_for_user(self, user_id: str, task_id: str) -> TaskRead | None:
        row = self.connection.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        ).fetchone()
        if row is None:
            return None
        return self._task_from_row(row)

    def _task_from_row(self, row: sqlite3.Row) -> TaskRead:
        return TaskRead(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            due_at=self._parse_datetime_value(row["due_at"]),
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
        self.connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, due_at = ?, priority = ?, updated_at = ?
            WHERE user_id = ? AND id = ?
            """,
            (
                updated.title,
                updated.description,
                updated.due_at.isoformat() if updated.due_at else None,
                updated.priority,
                updated.updated_at.isoformat(),
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
        self.connection.execute(
            "UPDATE tasks SET is_completed = ?, updated_at = ? WHERE user_id = ? AND id = ?",
            (int(task.is_completed), task.updated_at.isoformat(), user_id, task_id),
        )
        self.connection.commit()
        return task

    def delete_task_for_user(self, user_id: str, task_id: str) -> bool:
        cursor = self.connection.execute(
            "DELETE FROM tasks WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        )
        self.connection.commit()
        return cursor.rowcount > 0

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
        self.connection.execute(
            """
            INSERT INTO reminders (id, user_email, title, message, channel, scheduled_for, sent_at, is_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reminder["id"],
                reminder["user_email"],
                reminder["title"],
                reminder["message"],
                reminder["channel"],
                reminder["scheduled_for"].isoformat(),
                None,
                0,
            ),
        )
        self.connection.commit()
        return reminder

    def list_reminders(self) -> list[ReminderRead]:
        rows = self.connection.execute("SELECT * FROM reminders ORDER BY scheduled_for ASC").fetchall()
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
                    sent_at=self._parse_datetime_value(row["sent_at"]),
                    is_sent=bool(row["is_sent"]),
                )
            )
        return reminders

    def list_due_reminders(self, now: datetime) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM reminders WHERE is_sent = 0 AND scheduled_for <= ? ORDER BY scheduled_for ASC",
            (now.isoformat(),),
        ).fetchall()
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
                    "sent_at": self._parse_datetime_value(row["sent_at"]),
                    "is_sent": bool(row["is_sent"]),
                }
            )
        return reminders

    def mark_reminder_sent(self, reminder_id: str) -> None:
        self.connection.execute(
            "UPDATE reminders SET sent_at = ?, is_sent = 1 WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), reminder_id),
        )
        self.connection.commit()


__all__ = ["SQLiteStore"]
