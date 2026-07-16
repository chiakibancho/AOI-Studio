import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.api.v1.endpoints._common import _get_project_for_user
from app.models.music_analysis import MusicAnalysis
from app.models.user import User
from app.schemas.music_analysis import MusicAnalysisResponse
from app.services import music_analysis_service
from app.services.music_analysis_service import UnsupportedAudioFormatError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/music-analysis", response_model=MusicAnalysisResponse)
async def analyze_music(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """アップロードされた音声ファイル（mp3/wav）をessentiaで解析し、結果をDBに保存して返す。

    プロジェクトごとに1件（再アップロードで上書き）。
    """
    project = await _get_project_for_user(project_id, current_user, db)

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="空のファイルです",
        )

    try:
        result = await music_analysis_service.analyze_audio_file(file.filename or "", content)
    except UnsupportedAudioFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    existing_result = await db.execute(
        select(MusicAnalysis).where(MusicAnalysis.project_id == project.id)
    )
    analysis = existing_result.scalar_one_or_none()
    if analysis is None:
        analysis = MusicAnalysis(project_id=project.id)
        db.add(analysis)

    analysis.filename = file.filename or ""
    analysis.bpm = result["bpm"]
    analysis.key = result["key"]
    analysis.scale = result["scale"]
    analysis.key_strength = result["key_strength"]
    analysis.analyzed_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(analysis)
    return MusicAnalysisResponse.model_validate(analysis)


@router.get("/music-analysis", response_model=MusicAnalysisResponse)
async def get_music_analysis(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存済みの音楽解析結果を取得する（再アップロード不要）。なければ404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(MusicAnalysis).where(MusicAnalysis.project_id == project.id)
    )
    analysis = result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MusicAnalysis not found",
        )
    return MusicAnalysisResponse.model_validate(analysis)
