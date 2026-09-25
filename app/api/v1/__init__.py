"""Version 1 API package."""

from .auth import router as auth_router
from .health import router as health_router
from .reminders import router as reminders_router
from .tasks import router as tasks_router

__all__ = ["auth_router", "health_router", "reminders_router", "tasks_router"]
