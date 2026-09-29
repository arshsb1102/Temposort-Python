from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.environment import settings

celery_app = Celery(
    "temposort",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "daily-reminder-digest": {
            "task": "app.services.tasks.process_due_reminders_task",
            "schedule": crontab(
                minute=settings.reminder_digest_minute,
                hour=settings.reminder_digest_hour,
            ),
            "options": {"queue": "default"},
        }
    }
    if settings.reminder_digest_enabled
    else {},
)

__all__ = ["celery_app"]
