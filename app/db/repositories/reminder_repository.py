from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.db.repositories.base import BaseRepository
from app.schemas import ReminderCreate, ReminderRead


class ReminderRepository(BaseRepository):
    def create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        reminder_id = __import__("uuid").uuid4().hex
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
        with self.session.cursor() as cursor:
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
        self.session.connection.commit()
        return reminder

    async def async_create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        return await asyncio.to_thread(self.create_reminder, payload)

    def list_reminders(self) -> list[ReminderRead]:
        with self.session.cursor() as cursor:
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

    async def async_list_reminders(self) -> list[ReminderRead]:
        return await asyncio.to_thread(self.list_reminders)

    def list_due_reminders(self, now: datetime) -> list[dict[str, Any]]:
        with self.session.cursor() as cursor:
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

    async def async_list_due_reminders(self, now: datetime) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.list_due_reminders, now)

    def mark_reminder_sent(self, reminder_id: str) -> None:
        with self.session.cursor() as cursor:
            cursor.execute(
                "UPDATE reminders SET sent_at = %s, is_sent = TRUE WHERE id = %s",
                (datetime.now(timezone.utc), reminder_id),
            )
        self.session.connection.commit()

    async def async_mark_reminder_sent(self, reminder_id: str) -> None:
        await asyncio.to_thread(self.mark_reminder_sent, reminder_id)
