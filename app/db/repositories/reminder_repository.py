from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models import Reminder
from app.schemas import ReminderCreate, ReminderRead


class ReminderRepository:
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _to_read(reminder: Reminder) -> ReminderRead:
        return ReminderRead(
            id=reminder.id,
            user_email=reminder.user_email,
            title=reminder.title,
            message=reminder.message,
            channel=reminder.channel,
            scheduled_for=reminder.scheduled_for,
            sent_at=reminder.sent_at,
            is_sent=reminder.is_sent,
        )

    async def create_reminder(self, payload: ReminderCreate) -> dict[str, Any]:
        async with self.session_factory() as session:
            reminder = Reminder(
                user_email=payload.user_email.lower(),
                title=payload.title,
                message=payload.message,
                channel=payload.channel,
                scheduled_for=payload.scheduled_for,
                sent_at=None,
                is_sent=False,
            )
            session.add(reminder)
            await session.commit()
            await session.refresh(reminder)
            return {
                "id": reminder.id,
                "user_email": reminder.user_email,
                "title": reminder.title,
                "message": reminder.message,
                "channel": reminder.channel,
                "scheduled_for": reminder.scheduled_for,
                "sent_at": reminder.sent_at,
                "is_sent": reminder.is_sent,
            }

    async def list_reminders(self, user_email: str) -> list[ReminderRead]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Reminder)
                .where(Reminder.user_email == user_email.lower())
                .order_by(Reminder.scheduled_for.asc())
            )
            reminders = result.scalars().all()
            return [self._to_read(reminder) for reminder in reminders]

    async def list_due_reminders(self, now: datetime, user_email: str | None = None) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            due_query = select(Reminder).where(
                Reminder.is_sent.is_(False),
                Reminder.scheduled_for <= now,
            )
            if user_email is not None:
                due_query = due_query.where(Reminder.user_email == user_email.lower())
            result = await session.execute(due_query.order_by(Reminder.scheduled_for.asc()))
            reminders = result.scalars().all()
            return [
                {
                    "id": reminder.id,
                    "user_email": reminder.user_email,
                    "title": reminder.title,
                    "message": reminder.message,
                    "channel": reminder.channel,
                    "scheduled_for": reminder.scheduled_for,
                    "sent_at": reminder.sent_at,
                    "is_sent": reminder.is_sent,
                }
                for reminder in reminders
            ]

    async def mark_reminder_sent(self, reminder_id: str) -> None:
        async with self.session_factory() as session:
            result = await session.execute(select(Reminder).where(Reminder.id == reminder_id))
            reminder = result.scalar_one_or_none()
            if reminder is None:
                return

            reminder.sent_at = datetime.now(timezone.utc)
            reminder.is_sent = True
            await session.commit()
