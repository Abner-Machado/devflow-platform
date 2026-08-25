"""Project CRUD."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentUser, DbSession, Pagination, get_owned_project
from app.models.enums import ActivityAction, Priority, ProjectStatus
from app.models.project import Project
from app.schemas.common import Message, Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import metrics as metrics_service
from app.services.activity import record

router = APIRouter(prefix="/projects", tags=["projects"])

SORTABLE = {
    "created_at": Project.created_at,
    "updated_at": Project.updated_at,
    "name": Project.name,
    "priority": Project.priority,
    "status": Project.status,
}


def serialize_projects(db: DbSession, projects: list[Project]) -> list[ProjectRead]:
    """Attach derived stats to each project using a single grouped query."""
    stats = metrics_service.project_stats_map(db, [project.id for project in projects])
    payload = []
    for project in projects:
        item = ProjectRead.model_validate(project)
        item.stats = stats[project.id]
        payload.append(item)
    return payload


@router.get("", response_model=Page[ProjectRead], summary="List the caller's projects")
def list_projects(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    status_filter: Annotated[
        ProjectStatus | None, Query(alias="status", description="Filter by project status.")
    ] = None,
    priority: Annotated[Priority | None, Query(description="Filter by priority.")] = None,
    search: Annotated[
        str | None, Query(min_length=1, max_length=120, description="Match name or description.")
    ] = None,
    sort_by: Annotated[
        str, Query(description="One of: created_at, updated_at, name, priority, status.")
    ] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[ProjectRead]:
    filters = [Project.owner_id == current_user.id]
    if status_filter is not None:
        filters.append(Project.status == status_filter)
    if priority is not None:
        filters.append(Project.priority == priority)
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Project.name).like(pattern),
                func.lower(func.coalesce(Project.description, "")).like(pattern),
            )
        )

    total = int(
        db.execute(select(func.count()).select_from(Project).where(*filters)).scalar_one() or 0
    )
    column = SORTABLE.get(sort_by, Project.created_at)
    ordering = column.asc() if order == "asc" else column.desc()
    rows = (
        db.execute(
            select(Project)
            .where(*filters)
            .order_by(ordering)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    return Page.build(
        serialize_projects(db, list(rows)), total, pagination.page, pagination.page_size
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession, current_user: CurrentUser) -> ProjectRead:
    project = Project(
        name=payload.name.strip(),
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        repository_url=str(payload.repository_url) if payload.repository_url else None,
        owner_id=current_user.id,
    )
    db.add(project)
    db.flush()
    record(
        db,
        user=current_user,
        action=ActivityAction.PROJECT_CREATED,
        entity_type="project",
        entity_title=project.name,
        entity_id=project.id,
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return serialize_projects(db, [project])[0]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> ProjectRead:
    project = get_owned_project(db, project_id, current_user)
    return serialize_projects(db, [project])[0]


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: uuid.UUID, payload: ProjectUpdate, db: DbSession, current_user: CurrentUser
) -> ProjectRead:
    project = get_owned_project(db, project_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "repository_url" in changes and changes["repository_url"] is not None:
        changes["repository_url"] = str(changes["repository_url"])
    for field, value in changes.items():
        setattr(project, field, value)

    if changes:
        record(
            db,
            user=current_user,
            action=ActivityAction.PROJECT_UPDATED,
            entity_type="project",
            entity_title=project.name,
            entity_id=project.id,
            project_id=project.id,
        )
    db.commit()
    db.refresh(project)
    return serialize_projects(db, [project])[0]


@router.delete("/{project_id}", response_model=Message)
def delete_project(project_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> Message:
    """Deleting a project cascades to its tasks and documents."""
    project = get_owned_project(db, project_id, current_user)
    name = project.name
    db.delete(project)
    db.flush()
    record(
        db,
        user=current_user,
        action=ActivityAction.PROJECT_DELETED,
        entity_type="project",
        entity_title=name,
    )
    db.commit()
    return Message(message=f"Project '{name}' deleted.")
