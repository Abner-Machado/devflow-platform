"""Append-only activity log."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, utcnow
from app.models.enums import ActivityAction

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project
    from app.models.user import User


class Activity(UUIDPrimaryKeyMixin, Base):
    """One row per meaningful state change.

    The row keeps a denormalised entity_title and summary so the feed stays
    readable after the entity it refers to has been deleted.
    """

    __tablename__ = "activities"

    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, native_enum=False, length=30, validate_strings=True),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), nullable=True)
    entity_title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    summary: Mapped[str] = mapped_column(String(400), nullable=False)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    user: Mapped["User"] = relationship()
    project: Mapped["Project | None"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Activity {self.action}>"
