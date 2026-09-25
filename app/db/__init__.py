from __future__ import annotations

from app.core.environment import settings
from app.storage.postgres_store import PostgresStore

store = PostgresStore(settings.database_url)

__all__ = ["store"]
