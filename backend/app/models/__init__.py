"""SQLAlchemy models.

Importing this package registers every mapper on Base.metadata, which is what
Alembic autogenerate and create_all rely on.
"""

from app.db.base import Base
from app.models.activity import Activity
from app.models.document import Document
from app.models.enums import (
    ACTIVE_PROJECT_STATUSES,
    OPEN_TASK_STATUSES,
    ActivityAction,
    Priority,
    ProjectStatus,
    TaskStatus,
)
from app.models.project import Project
from app.models.task import Task
from app.models.user import RefreshToken, User

__all__ = [
    "ACTIVE_PROJECT_STATUSES",
    "OPEN_TASK_STATUSES",
    "Activity",
    "ActivityAction",
    "Base",
    "Document",
    "Priority",
    "Project",
    "ProjectStatus",
    "RefreshToken",
    "Task",
    "TaskStatus",
    "User",
]
