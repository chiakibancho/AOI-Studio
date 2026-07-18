from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.character import CharacterStatus


class CharacterCreateRequest(BaseModel):
    name: str
    prompt: str


class CharacterUpdateRequest(BaseModel):
    name: str = Field(min_length=1)


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    prompt: str
    sheet_image_path: Optional[str]
    status: CharacterStatus
    error_message: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
