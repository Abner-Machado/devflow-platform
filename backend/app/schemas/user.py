"""User schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.config import settings


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)


class UserCreate(UserBase):
    password: str = Field(
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=72,  # bcrypt only hashes the first 72 bytes; reject longer inputs up front.
        description="Plaintext password. Hashed with bcrypt before storage.",
    )


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(
        default=None, min_length=settings.PASSWORD_MIN_LENGTH, max_length=72
    )


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class UserSummary(BaseModel):
    """Compact user representation embedded in task and document payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
