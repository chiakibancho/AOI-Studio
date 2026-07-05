from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.structure import Structure
from app.models.user import User
from app.models.video_spec import VideoSpec
from app.schemas.structure import StructureResponse
from app.schemas.video_spec import VideoSpecCreate, VideoSpecResponse
from app.services import ai_service

router = APIRouter()


async def _get_project_for_user(
    project_id: str,
    current_user: User,
    db: AsyncSession,
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


# ---------------------------------------------------------------------------
# VideoSpec endpoints
# ---------------------------------------------------------------------------


@router.put("/spec", response_model=VideoSpecResponse)
async def upsert_video_spec(
    project_id: str,
    request: VideoSpecCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """VideoSpec を upsert する（既存あれば更新、なければ作成）。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(VideoSpec).where(VideoSpec.project_id == project.id)
    )
    spec = result.scalar_one_or_none()

    if spec is None:
        spec = VideoSpec(
            project_id=project.id,
            duration_sec=request.duration_sec,
            target_audience=request.target_audience,
            message=request.message,
            mood=request.mood,
            style_notes=request.style_notes,
            reference_urls=request.reference_urls,
        )
        db.add(spec)
    else:
        spec.duration_sec = request.duration_sec
        spec.target_audience = request.target_audience
        spec.message = request.message
        spec.mood = request.mood
        spec.style_notes = request.style_notes
        spec.reference_urls = request.reference_urls
        spec.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(spec)
    return VideoSpecResponse.model_validate(spec)


@router.get("/spec", response_model=VideoSpecResponse)
async def get_video_spec(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """VideoSpec を取得する。なければ 404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(VideoSpec).where(VideoSpec.project_id == project.id)
    )
    spec = result.scalar_one_or_none()
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VideoSpec not found",
        )
    return VideoSpecResponse.model_validate(spec)


# ---------------------------------------------------------------------------
# Structure endpoints
# ---------------------------------------------------------------------------


@router.post("/structure/generate", response_model=StructureResponse, status_code=201)
async def generate_structure(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI で Structure を生成する。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    # VideoSpec が必要
    spec_result = await db.execute(
        select(VideoSpec).where(VideoSpec.project_id == project.id)
    )
    spec = spec_result.scalar_one_or_none()
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VideoSpec が存在しません。先に /spec を登録してください。",
        )

    # 既存の最新バージョンを確認
    latest_result = await db.execute(
        select(Structure)
        .where(Structure.project_id == project.id)
        .order_by(Structure.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    next_version = (latest.version + 1) if latest else 1

    # AI で構成を生成
    ai_result = await ai_service.generate_structure(project, spec)

    structure = Structure(
        project_id=project.id,
        scenes=ai_result.get("scenes", []),
        rationale=ai_result.get("rationale", ""),
        total_duration_sec=ai_result.get("total_duration_sec", 0),
        version=next_version,
    )
    db.add(structure)

    # プロジェクトの status を "structure" に更新
    project.status = ProjectStatus.structure

    await db.flush()
    await db.refresh(structure)
    return StructureResponse.model_validate(structure)


@router.get("/structure", response_model=StructureResponse)
async def get_structure(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新の Structure を取得する（version 降順で最初の1件）。なければ 404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Structure)
        .where(Structure.project_id == project.id)
        .order_by(Structure.version.desc())
        .limit(1)
    )
    structure = result.scalar_one_or_none()
    if structure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure not found",
        )
    return StructureResponse.model_validate(structure)


@router.post("/structure/approve", response_model=StructureResponse)
async def approve_structure(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 Structure を承認し、プロジェクト status を 'storyboard' に更新する。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Structure)
        .where(Structure.project_id == project.id)
        .order_by(Structure.version.desc())
        .limit(1)
    )
    structure = result.scalar_one_or_none()
    if structure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure not found",
        )

    structure.approved_at = datetime.now(timezone.utc)
    project.status = ProjectStatus.storyboard

    await db.flush()
    await db.refresh(structure)
    return StructureResponse.model_validate(structure)
