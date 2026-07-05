from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.project import ProjectStatus, VideoType


class ProjectCreate(BaseModel):
    title: str
    video_type: VideoType


class ProjectResponse(BaseModel):
    id: str
    user_id: str
    organization_id: Optional[str]
    title: str
    video_type: VideoType
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
