import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import engine
from app.services.queue_observability import queue_observability

router = APIRouter(prefix="/api/v1", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict[str, object]:
    health = queue_observability.snapshot()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError:
        logger.exception("Database readiness check failed")
        database_ok = False

    return {
        "status": "ok" if database_ok and health["redis_ok"] and health["celery_ok"] else "degraded",
        "service": "tempoSort-fastapi",
        "database_ok": database_ok,
        **health,
    }
