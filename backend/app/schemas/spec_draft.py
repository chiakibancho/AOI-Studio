from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.spec_draft import SpecDraftStatus


class SpecDraftGenerateRequest(BaseModel):
    raw_input: str = Field(..., min_length=1, max_length=4000)


class SpecDraftResponse(BaseModel):
    id: str
    project_id: str
    raw_input: str
    duration_sec: int
    target_audience: str
    message: str
    mood: str
    style_notes: Optional[str]
    reference_urls: list[str]
    rationale: str
    version: int
    status: SpecDraftStatus
    error_message: Optional[str]
    approved_at: Optional[datetime]
    generated_at: datetime

    model_config = {"from_attributes": True}
