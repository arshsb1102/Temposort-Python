from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserRead(BaseModel):
    id: str
    name: str
    email: str
    is_verified: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerificationStatus(BaseModel):
    verified: bool
    email: str
    message: str


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str | None = None
    due_at: datetime | None = None
    priority: Literal["low", "medium", "high"] = "medium"


class TaskRead(TaskCreate):
    id: str
    is_completed: bool = False
    created_at: datetime
    updated_at: datetime


class ReminderCreate(BaseModel):
    user_email: EmailStr
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    channel: Literal["email", "sms", "push"] = "email"
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
