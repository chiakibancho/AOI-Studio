from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.storyboard import StoryboardStatus


class StoryboardSceneAI(BaseModel):
    """AIが生成する形（time_start/time_endはバックエンドが計算するため含まない）。"""

    scene_number: int
    intent: str
    composition: str
    camera_work: str
    text_overlay: str


class StoryboardScene(BaseModel):
    """永続化・レスポンス形（AI生成フィールド + バックエンド計算のtime_start/time_end）。"""

    scene_number: int
    time_start: int
    time_end: int
    intent: str
    composition: str
    camera_work: str
    text_overlay: str


class StoryboardResponse(BaseModel):
    id: str
    project_id: str
    structure_id: str
    scenes: list[StoryboardScene]
    version: int
    status: StoryboardStatus
    error_message: Optional[str]
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
