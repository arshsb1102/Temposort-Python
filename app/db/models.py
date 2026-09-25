from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserRecord:
    id: str
    name: str
    email: str
    password_hash: str
    is_verified: bool = False
    created_at: datetime | None = None


@dataclass(slots=True)
class TaskRecord:
    id: str
    user_id: str
    title: str
    description: str | None
    due_at: datetime | None
    priority: str
    is_completed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ReminderRecord:
    id: str
    user_email: str
    title: str
    message: str
    channel: str
    scheduled_for: datetime
    sent_at: datetime | None = None
    is_sent: bool = False
