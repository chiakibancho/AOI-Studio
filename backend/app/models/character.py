import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CharacterStatus(str, enum.Enum):
    draft = "draft"
    generating = "generating"
    generated = "generated"
    failed = "failed"
    approved = "approved"


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    variables: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    template_version: Mapped[str] = mapped_column(String(16), nullable=False)
    sheet_image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[CharacterStatus] = mapped_column(
        Enum(CharacterStatus, name="characterstatus"),
        default=CharacterStatus.draft,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["Project"] = relationship("Project", back_populates="characters")  # noqa: F821
