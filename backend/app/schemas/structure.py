from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SceneItem(BaseModel):
    number: int
    title: str
    duration_sec: int
    description: str
    shot_type: str
    mood: str
    notes: str


class StructureResponse(BaseModel):
    id: str
    project_id: str
    scenes: list[Any]
    rationale: str
    total_duration_sec: int
    version: int
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
