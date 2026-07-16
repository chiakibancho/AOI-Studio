from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.character import CharacterStatus


class TemplateVariablesResponse(BaseModel):
    template_version: str
    variables: list[str]


class CharacterCreateRequest(BaseModel):
    name: str
    variables: dict[str, str]


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    variables: dict[str, str]
    template_version: str
    sheet_image_path: Optional[str]
    status: CharacterStatus
    error_message: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
