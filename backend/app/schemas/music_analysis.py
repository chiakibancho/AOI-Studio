from datetime import datetime

from pydantic import BaseModel


class MusicAnalysisResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    bpm: float
    key: str
    scale: str
    key_strength: float
    analyzed_at: datetime

    model_config = {"from_attributes": True}
