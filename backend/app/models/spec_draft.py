import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SpecDraftStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class SpecDraft(Base):
    __tablename__ = "spec_drafts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mood: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    style_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_urls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[SpecDraftStatus] = mapped_column(
        Enum(SpecDraftStatus, name="specdraftstatus"),
        default=SpecDraftStatus.pending,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="spec_drafts")  # noqa: F821
