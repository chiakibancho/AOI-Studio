from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.models.shooting_list import ShootingListStatus

ShotCategory = Literal["exterior", "people", "product", "broll", "other"]


class ShootingListShotAI(BaseModel):
    """AIが生成する形（cut_number/completedはバックエンドが計算するため含まない）。"""

    scene_number: int
    category: ShotCategory
    title: str
    location: str
    equipment: str
    talent_props: str
    notes: str


class ShootingListShot(BaseModel):
    """永続化・レスポンス形（AI生成フィールド + バックエンド計算のcut_number/completed）。"""

    cut_number: int
    scene_number: int
    category: ShotCategory
    title: str
    location: str
    equipment: str
    talent_props: str
    notes: str
    completed: bool


class ShootingListShotToggleRequest(BaseModel):
    completed: bool


class ShootingListResponse(BaseModel):
    id: str
    project_id: str
    storyboard_id: str
    shots: list[ShootingListShot]
    version: int
    status: ShootingListStatus
    error_message: Optional[str]
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
