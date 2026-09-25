from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db.session import DatabaseSession


class BaseRepository:
    def __init__(self, session: DatabaseSession) -> None:
        self.session = session

    def _row_to_dict(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def _parse_datetime_value(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
