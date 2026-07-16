from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.shot_image import ShotImageStatus


class ShotImageGenerateRequest(BaseModel):
    style: str = ""


class ShotImageResponse(BaseModel):
    id: str
    project_id: str
    shooting_list_id: str
    cut_number: int
    image_path: Optional[str]
    status: ShotImageStatus
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
