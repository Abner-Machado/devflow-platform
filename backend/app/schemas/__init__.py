"""Pydantic request/response models."""

from app.schemas.activity import ActivityRead
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, TokenPair
from app.schemas.common import ErrorResponse, Message, Page
from app.schemas.dashboard import DashboardResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
)
from app.schemas.metrics import MetricsOverview, MetricsResponse
from app.schemas.project import ProjectCreate, ProjectRead, ProjectStats, ProjectUpdate
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.schemas.user import UserCreate, UserRead, UserSummary, UserUpdate

__all__ = [
    "ActivityRead",
    "AuthResponse",
    "DashboardResponse",
    "DocumentCreate",
    "DocumentRead",
    "DocumentSummary",
    "DocumentUpdate",
    "ErrorResponse",
    "LoginRequest",
    "Message",
    "MetricsOverview",
    "MetricsResponse",
    "Page",
    "ProjectCreate",
    "ProjectRead",
    "ProjectStats",
    "ProjectUpdate",
    "RefreshRequest",
    "TaskCreate",
    "TaskRead",
    "TaskUpdate",
    "TokenPair",
    "UserCreate",
    "UserRead",
    "UserSummary",
    "UserUpdate",
]
