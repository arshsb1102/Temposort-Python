from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.core.environment import settings

celery_app = Celery(
    "temposort",
    broker=settings.redis_url,
    backend=settings.celery_result_backend_url,
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
    task_default_queue="temposort",
    task_queues=(Queue("temposort", durable=True),),
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=3600,
    result_backend_transport_options={"visibility_timeout": 3600},
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    task_time_limit=120,
    task_soft_time_limit=90,
    beat_schedule={
        "daily-reminder-digest": {
            "task": "app.services.tasks.process_due_reminders_task",
            "schedule": crontab(
                minute=settings.reminder_digest_minute,
                hour=settings.reminder_digest_hour,
            ),
            "options": {"queue": "temposort"},
        }
    }
    if settings.reminder_digest_enabled
    else {},
)

__all__ = ["celery_app"]
