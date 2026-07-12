from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.structure import StructureStatus


class SceneItem(BaseModel):
    number: int
    title: str
    duration_sec: int
    description: str
    shot_type: str
    mood: str
    notes: str


class StructureOption(BaseModel):
    scenes: list[SceneItem]
    rationale: str
    total_duration_sec: int


class StructureResponse(BaseModel):
    id: str
    project_id: str
    scenes: list[SceneItem]
    rationale: str
    total_duration_sec: int
    options: list[StructureOption]
    version: int
    status: StructureStatus
    error_message: Optional[str]
    selected_option_index: Optional[int]
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
