from __future__ import annotations

from app.core.environment import settings
from app.storage.postgres_store import PostgresStore
from app.storage.sqlite_store import SQLiteStore

if settings.database_url.startswith("sqlite"):
    sqlite_path = settings.database_url.replace("sqlite:///", "") if settings.database_url.startswith("sqlite:///") else settings.database_url
    store = SQLiteStore(sqlite_path)
else:
    store = PostgresStore(settings.database_url)

__all__ = ["store"]
