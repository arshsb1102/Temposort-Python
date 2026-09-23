from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.tasks import router as tasks_router

app = FastAPI(
    title="TempoSort FastAPI",
    version="0.2.0",
    description="Production-aligned FastAPI starter for the TempoSort backend.",
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(tasks_router)
