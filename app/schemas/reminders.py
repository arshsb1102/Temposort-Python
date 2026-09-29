from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ReminderCreate(BaseModel):
    user_email: EmailStr
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    channel: Literal["email"] = "email"
    scheduled_for: datetime


class ReminderRead(BaseModel):
    id: str
    user_email: str
    title: str
    message: str
    channel: str
    scheduled_for: datetime
    sent_at: datetime | None = None
    is_sent: bool = False
