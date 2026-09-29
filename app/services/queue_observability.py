from __future__ import annotations

from threading import Lock
from time import monotonic
from typing import Any

from app.services.celery_app import celery_app
from app.services.redis_service import redis_service
from app.services.telemetry import CELERY_WORKERS, QUEUE_DEPTH


class QueueObservability:
    def __init__(self, worker_stats_ttl_seconds: float = 5.0) -> None:
        self.worker_stats_ttl_seconds = worker_stats_ttl_seconds
        self._worker_stats: dict[str, Any] = {}
        self._worker_stats_checked_at = 0.0
        self._worker_stats_lock = Lock()

    def _get_worker_stats(self) -> dict[str, Any]:
        now = monotonic()
        with self._worker_stats_lock:
            if now - self._worker_stats_checked_at >= self.worker_stats_ttl_seconds:
                try:
                    self._worker_stats = celery_app.control.inspect(timeout=0.25).stats() or {}
                except Exception:
                    self._worker_stats = {}
                self._worker_stats_checked_at = monotonic()
            return self._worker_stats

    def snapshot(self) -> dict[str, Any]:
        redis_ok = redis_service.ping()
        worker_stats = self._get_worker_stats()
        CELERY_WORKERS.set(len(worker_stats))

        queue_depth = None
        if redis_ok:
            try:
                queue_depth = redis_service.queue_length("temposort")
                QUEUE_DEPTH.set(queue_depth)
            except Exception:
                redis_ok = False

        return {
            "redis_ok": redis_ok,
            "celery_ok": bool(worker_stats),
            "worker_count": len(worker_stats),
            "queue_depth": queue_depth,
            "queue": "temposort",
        }


queue_observability = QueueObservability()

__all__ = ["queue_observability", "QueueObservability"]
