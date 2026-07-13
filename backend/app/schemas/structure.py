from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

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


class StructureReviseRequest(BaseModel):
    feedback: str = Field(..., min_length=1, max_length=1000)


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
    human_feedback: Optional[str]
    based_on_structure_id: Optional[str]
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
