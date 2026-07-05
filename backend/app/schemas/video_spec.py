from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VideoSpecCreate(BaseModel):
    duration_sec: int = Field(..., ge=5, le=3600)
    target_audience: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=1000)
    mood: str = Field(..., min_length=1, max_length=100)
    style_notes: Optional[str] = Field(None, max_length=1000)
    reference_urls: list[str] = Field(default_factory=list, max_length=10)


class VideoSpecResponse(BaseModel):
    id: str
    project_id: str
    duration_sec: int
    target_audience: str
    message: str
    mood: str
    style_notes: Optional[str]
    reference_urls: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
