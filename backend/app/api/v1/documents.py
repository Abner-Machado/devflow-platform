"""Markdown documentation attached to projects."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import (
    CurrentUser,
    DbSession,
    Pagination,
    get_owned_document,
    get_owned_project,
)
from app.models.document import Document
from app.models.enums import ActivityAction
from app.models.project import Project
from app.schemas.common import Message, Page
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
)
from app.services.activity import record

router = APIRouter(prefix="/documents", tags=["documents"])

EXCERPT_LENGTH = 180


def _excerpt(content: str) -> str:
    """First body line of the Markdown, trimmed for list views.

    Headings are skipped: the top one usually repeats the title, which would
    make every row in the list read twice.
    """
    fallback = ""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            fallback = fallback or stripped.lstrip("#").strip()
            continue
        return stripped[:EXCERPT_LENGTH]
    return fallback[:EXCERPT_LENGTH]


def _summary(document: Document) -> DocumentSummary:
    item = DocumentSummary.model_validate(document)
    item.project_name = document.project.name if document.project else None
    item.excerpt = _excerpt(document.content)
    return item


def _detail(document: Document) -> DocumentRead:
    item = DocumentRead.model_validate(document)
    item.project_name = document.project.name if document.project else None
    return item


@router.get("", response_model=Page[DocumentSummary], summary="List and search documents")
def list_documents(
    db: DbSession,
    current_user: CurrentUser,
    pagination: Pagination,
    project_id: Annotated[uuid.UUID | None, Query()] = None,
    search: Annotated[
        str | None, Query(min_length=1, max_length=200, description="Match title or body.")
    ] = None,
) -> Page[DocumentSummary]:
    owned_projects = select(Project.id).where(Project.owner_id == current_user.id)
    filters = [Document.project_id.in_(owned_projects)]

    if project_id is not None:
        get_owned_project(db, project_id, current_user)
        filters.append(Document.project_id == project_id)
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Document.title).like(pattern),
                func.lower(Document.content).like(pattern),
            )
        )

    total = int(
        db.execute(select(func.count()).select_from(Document).where(*filters)).scalar_one() or 0
    )
    rows = (
        db.execute(
            select(Document)
            .where(*filters)
            .options(selectinload(Document.project))
            .order_by(Document.updated_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        .scalars()
        .all()
    )
    return Page.build(
        [_summary(document) for document in rows], total, pagination.page, pagination.page_size
    )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate, db: DbSession, current_user: CurrentUser
) -> DocumentRead:
    project = get_owned_project(db, payload.project_id, current_user)
    document = Document(
        title=payload.title.strip(),
        content=payload.content,
        project_id=project.id,
        author_id=current_user.id,
    )
    db.add(document)
    db.flush()
    record(
        db,
        user=current_user,
        action=ActivityAction.DOCUMENT_CREATED,
        entity_type="document",
        entity_title=document.title,
        entity_id=document.id,
        project_id=project.id,
    )
    db.commit()
    db.refresh(document)
    return _detail(document)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> DocumentRead:
    return _detail(get_owned_document(db, document_id, current_user))


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: uuid.UUID, payload: DocumentUpdate, db: DbSession, current_user: CurrentUser
) -> DocumentRead:
    document = get_owned_document(db, document_id, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "project_id" in changes and changes["project_id"] is not None:
        get_owned_project(db, changes["project_id"], current_user)
    for field, value in changes.items():
        setattr(document, field, value)

    if changes:
        record(
            db,
            user=current_user,
            action=ActivityAction.DOCUMENT_UPDATED,
            entity_type="document",
            entity_title=document.title,
            entity_id=document.id,
            project_id=document.project_id,
        )
    db.commit()
    db.refresh(document)
    return _detail(document)


@router.delete("/{document_id}", response_model=Message)
def delete_document(document_id: uuid.UUID, db: DbSession, current_user: CurrentUser) -> Message:
    document = get_owned_document(db, document_id, current_user)
    title, project_id = document.title, document.project_id
    db.delete(document)
    db.flush()
    record(
        db,
        user=current_user,
        action=ActivityAction.DOCUMENT_DELETED,
        entity_type="document",
        entity_title=title,
        project_id=project_id,
    )
    db.commit()
    return Message(message=f"Document '{title}' deleted.")
