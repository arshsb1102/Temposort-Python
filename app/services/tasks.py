from __future__ import annotations

from celery import Task

from app.services.celery_app import celery_app
from app.services.reminder_service import reminder_service


class ReminderDigestTask(Task):
    autoretry_for = (Exception,)
    max_retries = 5
    default_retry_delay = 30
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(bind=True, base=ReminderDigestTask, name="daily_reminder_digest")
def process_due_reminders_task(self) -> int:
    import asyncio

    try:
        return asyncio.run(reminder_service.process_due_reminders())
    except Exception:
        self.retry(exc=Exception(), countdown=30, max_retries=5)
        raise


__all__ = ["process_due_reminders_task"]
