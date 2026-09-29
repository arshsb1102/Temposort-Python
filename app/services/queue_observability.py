from __future__ import annotations

from typing import Any

from app.services.celery_app import celery_app
from app.services.redis_service import redis_service


class QueueObservability:
    def snapshot(self) -> dict[str, Any]:
        redis_ok = redis_service.ping()
        celery_ok = True
        try:
            celery_app.control.inspect().stats()
        except Exception:
            celery_ok = False
        return {
            "redis_ok": redis_ok,
            "celery_ok": celery_ok,
            "broker": redis_service.url,
            "queue": "default",
        }


queue_observability = QueueObservability()

__all__ = ["queue_observability", "QueueObservability"]
