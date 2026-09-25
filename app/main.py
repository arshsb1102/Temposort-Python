from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.reminders import router as reminders_router
from app.api.routes.tasks import router as tasks_router

app = FastAPI(
    title="TempoSort FastAPI",
    version="0.3.0",
    description="Production-aligned FastAPI starter for the TempoSort backend with email verification and reminder processing.",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(reminders_router)
