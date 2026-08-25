"""Activity feed schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActivityAction


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: ActivityAction
    entity_type: str
    entity_id: uuid.UUID | None
    entity_title: str
    summary: str
    project_id: uuid.UUID | None
    project_name: str | None = None
    created_at: datetime
