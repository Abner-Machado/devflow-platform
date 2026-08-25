"""Documentation schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserSummary


class DocumentBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(default="", max_length=200_000, description="Markdown body.")


class DocumentCreate(DocumentBase):
    project_id: uuid.UUID


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, max_length=200_000)
    project_id: uuid.UUID | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: str
    project_id: uuid.UUID
    project_name: str | None = None
    author: UserSummary | None = None
    created_at: datetime
    updated_at: datetime


class DocumentSummary(BaseModel):
    """List view: excludes the Markdown body to keep list responses small."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    project_id: uuid.UUID
    project_name: str | None = None
    excerpt: str = ""
    created_at: datetime
    updated_at: datetime
