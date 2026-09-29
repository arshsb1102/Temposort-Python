from fastapi import APIRouter

from app.services.queue_observability import queue_observability

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health_check() -> dict[str, object]:
    health = queue_observability.snapshot()
    return {
        "status": "ok" if health["redis_ok"] and health["celery_ok"] else "degraded",
        "service": "tempoSort-fastapi",
        **health,
    }
