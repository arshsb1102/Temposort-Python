from __future__ import annotations

from app.services.celery_app import celery_app
from app.services.reminder_service import reminder_service


@celery_app.task(name="daily_reminder_digest")
def process_due_reminders_task() -> int:
    import asyncio

    return asyncio.run(reminder_service.process_due_reminders())


__all__ = ["process_due_reminders_task"]
