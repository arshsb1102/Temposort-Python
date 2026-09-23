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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
