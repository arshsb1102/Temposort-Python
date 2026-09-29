from __future__ import annotations

import asyncio

from celery import Task
from redis.exceptions import RedisError
from sqlalchemy.exc import OperationalError

from app.db.base import engine
from app.services.celery_app import celery_app
from app.services.reminder_service import reminder_service
from app.services.email_transport import RetryableEmailDeliveryError
import app.services.telemetry
from app.services.telemetry import configure_worker_tracing

configure_worker_tracing()


class ReminderDigestTask(Task):
    autoretry_for = (RetryableEmailDeliveryError, OperationalError, RedisError)
    max_retries = 8
    retry_backoff = 5
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=ReminderDigestTask, name="app.services.tasks.process_due_reminders_task")
def process_due_reminders_task(user_email: str | None = None) -> int:
    async def process() -> int:
        try:
            return await reminder_service.process_due_reminders(user_email)
        finally:
            await engine.dispose()

    return asyncio.run(process())


__all__ = ["process_due_reminders_task"]
