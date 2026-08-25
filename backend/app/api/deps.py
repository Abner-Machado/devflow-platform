"""Reusable FastAPI dependencies: authentication, pagination, ownership lookups."""

import uuid
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.document import Document
from app.models.project import Project
from app.models.task import Task
from app.models.user import User

# auto_error=False so a missing header raises our own AuthenticationError and
# produces the same error envelope as every other failure.
bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token.")

    payload = decode_token(credentials.credentials, "access")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise AuthenticationError("Malformed token subject.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


class PaginationParams:
    """Page-number pagination, shared by every list endpoint."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="1-based page number.")] = 1,
        page_size: Annotated[int, Query(ge=1, le=100, description="Rows per page.")] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


Pagination = Annotated[PaginationParams, Depends(PaginationParams)]


def get_owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    """Fetch a project the caller owns, or 404.

    A project owned by someone else is reported as missing rather than forbidden,
    so the API does not leak the existence of other accounts' resources.
    """
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise NotFoundError("Project not found.")
    return project


def get_owned_task(db: Session, task_id: uuid.UUID, user: User) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project.owner_id != user.id:
        raise NotFoundError("Task not found.")
    return task


def get_owned_document(db: Session, document_id: uuid.UUID, user: User) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.project.owner_id != user.id:
        raise NotFoundError("Document not found.")
    return document
