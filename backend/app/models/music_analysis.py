import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MusicAnalysis(Base):
    __tablename__ = "music_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, unique=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    bpm: Mapped[float] = mapped_column(Float, nullable=False)
    key: Mapped[str] = mapped_column(String(8), nullable=False)
    scale: Mapped[str] = mapped_column(String(16), nullable=False)
    key_strength: Mapped[float] = mapped_column(Float, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    project: Mapped["Project"] = relationship("Project", back_populates="music_analysis")  # noqa: F821
