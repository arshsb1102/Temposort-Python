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
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_store_errors_even_if_ignored=True,
    worker_prefetch_multiplier=1,
    task_retry_backoff=True,
    task_retry_backoff_max=600,
    task_retry_jitter=True,
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
