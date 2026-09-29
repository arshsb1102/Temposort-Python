from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.tasks import router as tasks_router
from app.core.environment import settings
from app.services.redis_service import redis_service
from app.services.telemetry import RequestMetricsMiddleware, configure_tracing, metrics_response


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await redis_service.ping_async()
    except Exception:
        pass
    try:
        yield
    finally:
        await redis_service.close()


app = FastAPI(
    title="TempoSort FastAPI",
    version="0.3.0",
    description="Production-aligned FastAPI starter for the TempoSort backend with email verification and reminder processing.",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(reminders_router)
if settings.metrics_enabled:
    app.add_middleware(RequestMetricsMiddleware)
    app.add_api_route("/metrics", metrics_response, include_in_schema=False)
configure_tracing(app)
