from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.reminders import router as reminders_router
from app.api.v1.tasks import router as tasks_router
from app.services.scheduler import scheduler_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler_service.start()
    try:
        yield
    finally:
        scheduler_service.shutdown()


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
