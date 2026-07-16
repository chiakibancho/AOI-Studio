import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ShotImageStatus(str, enum.Enum):
    generating = "generating"
    generated = "generated"
    failed = "failed"


class ShotImage(Base):
    """撮影リストの1ショット（cut_number）に対する絵コンテイラスト生成の状態。

    shots自体はShootingList.shotsのJSONB配列要素であり独立したテーブルを持たないため、
    (shooting_list_id, cut_number)の組でショットを一意に特定する専用テーブルとして持つ。
    """

    __tablename__ = "shot_images"
    __table_args__ = (
        UniqueConstraint("shooting_list_id", "cut_number", name="uq_shot_images_list_cut"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    shooting_list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shooting_lists.id"), nullable=False, index=True
    )
    cut_number: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[ShotImageStatus] = mapped_column(
        Enum(ShotImageStatus, name="shotimagestatus"),
        default=ShotImageStatus.generating,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project: Mapped["Project"] = relationship("Project")  # noqa: F821
    shooting_list: Mapped["ShootingList"] = relationship("ShootingList")  # noqa: F821
