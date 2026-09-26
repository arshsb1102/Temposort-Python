from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.base import AsyncSessionLocal


class BaseRepository:
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
