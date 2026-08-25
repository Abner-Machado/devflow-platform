"""Project model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import Priority, ProjectStatus

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.document import Document
    from app.models.task import Task
    from app.models.user import User


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        # native_enum=False keeps the column a VARCHAR with a CHECK constraint, so
        # adding a value later is a plain migration on PostgreSQL and SQLite alike.
        Enum(ProjectStatus, native_enum=False, length=20, validate_strings=True),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, native_enum=False, length=20, validate_strings=True),
        default=Priority.MEDIUM,
        nullable=False,
        index=True,
    )
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Project {self.name}>"
