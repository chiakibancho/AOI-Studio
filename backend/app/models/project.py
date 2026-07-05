import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

import enum


class VideoType(str, enum.Enum):
    brand = "brand"
    corporate = "corporate"
    recruitment = "recruitment"
    sns_ad = "sns_ad"
    youtube = "youtube"
    short = "short"
    product_pr = "product_pr"


class ProjectStatus(str, enum.Enum):
    setup = "setup"
    music = "music"
    structure = "structure"
    storyboard = "storyboard"
    shooting = "shooting"
    upload = "upload"
    export = "export"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    organization_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    video_type: Mapped[VideoType] = mapped_column(
        Enum(VideoType, name="videotype"), nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="projectstatus"),
        default=ProjectStatus.setup,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="projects")  # noqa: F821
    organization: Mapped[Optional["Organization"]] = relationship(  # noqa: F821
        "Organization", back_populates="projects"
    )
    video_spec: Mapped[Optional["VideoSpec"]] = relationship("VideoSpec", back_populates="project", uselist=False)  # noqa: F821
    structures: Mapped[list["Structure"]] = relationship("Structure", back_populates="project", order_by="Structure.version.desc()")  # noqa: F821
