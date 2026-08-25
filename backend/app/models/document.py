"""Technical documentation model. Content is Markdown."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project
    from app.models.user import User


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="documents")
    author: Mapped["User | None"] = relationship(back_populates="documents")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Document {self.title}>"
