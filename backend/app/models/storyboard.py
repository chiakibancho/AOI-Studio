import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StoryboardStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Storyboard(Base):
    __tablename__ = "storyboards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    structure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("structures.id"), nullable=False, index=True
    )
    scenes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[StoryboardStatus] = mapped_column(
        Enum(StoryboardStatus, name="storyboardstatus"),
        default=StoryboardStatus.pending,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    based_on_storyboard_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("storyboards.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="storyboards")  # noqa: F821
