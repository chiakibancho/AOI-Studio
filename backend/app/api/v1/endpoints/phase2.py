import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.api.v1.endpoints._common import _advance_project_status, _get_project_for_user
from app.models.project import Project, ProjectStatus
from app.models.storyboard import Storyboard, StoryboardStatus
from app.models.structure import Structure
from app.models.user import User
from app.models.video_spec import VideoSpec
from app.schemas.storyboard import StoryboardReviseRequest, StoryboardSceneAI, StoryboardResponse
from app.services import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Storyboard endpoints
# ---------------------------------------------------------------------------


@router.post("/storyboard/generate", response_model=StoryboardResponse, status_code=202)
async def generate_storyboard(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """承認済みの Structure から絵コンテ生成をバックグラウンドで開始する。結果は GET /storyboard でポーリングする。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    structure_result = await db.execute(
        select(Structure)
        .where(Structure.project_id == project.id)
        .order_by(Structure.version.desc())
        .limit(1)
    )
    structure = structure_result.scalar_one_or_none()
    if structure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure not found",
        )
    if structure.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="承認済みのStructureがありません。先に構成案を承認してください。",
        )

    latest_result = await db.execute(
        select(Storyboard)
        .where(Storyboard.project_id == project.id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    if latest is not None and latest.status == StoryboardStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    next_version = (latest.version + 1) if latest else 1

    storyboard = Storyboard(
        project_id=project.id,
        structure_id=structure.id,
        scenes=[],
        version=next_version,
        status=StoryboardStatus.pending,
    )
    db.add(storyboard)
    await db.flush()
    await db.refresh(storyboard)

    background_tasks.add_task(run_storyboard_generation, storyboard.id)

    return StoryboardResponse.model_validate(storyboard)


def _validate_and_merge_storyboard_scenes(raw_scenes, structure_scenes: list) -> list[dict]:
    """AIの出力形状を検証し、Structureのシーンduration_secの累積和から計算した
    time_start/time_endとマージした最終的なscenesリストを返す。

    オール・オア・ナッシング: scene_number の集合が Structure のシーン番号と完全一致
    しない、あるいはいずれかの形が壊れていれば ValueError を投げる（呼び出し側で
    failed へ落とすことを想定）。
    """
    if not isinstance(raw_scenes, list):
        raise ValueError("AI応答に scenes 配列がありません")

    expected_numbers = {s["number"] for s in structure_scenes}
    got_numbers = {
        item.get("scene_number") if isinstance(item, dict) else None
        for item in raw_scenes
    }
    if got_numbers != expected_numbers:
        raise ValueError(
            f"AI応答の scene_number が構成のシーン番号と一致しません"
            f"（期待: {sorted(expected_numbers)}, 実際: {sorted(n for n in got_numbers if n is not None)}）"
        )

    validated = {
        item["scene_number"]: StoryboardSceneAI.model_validate(item).model_dump()
        for item in raw_scenes
    }

    # Structure のシーン duration_sec の累積和から time_start/time_end を計算する
    merged_scenes = []
    elapsed = 0
    for s in sorted(structure_scenes, key=lambda s: s["number"]):
        ai_scene = validated[s["number"]]
        time_start = elapsed
        time_end = elapsed + s["duration_sec"]
        merged_scenes.append(
            {
                "scene_number": s["number"],
                "time_start": time_start,
                "time_end": time_end,
                "intent": ai_scene["intent"],
                "composition": ai_scene["composition"],
                "camera_work": ai_scene["camera_work"],
                "text_overlay": ai_scene["text_overlay"],
            }
        )
        elapsed = time_end

    return merged_scenes


async def run_storyboard_generation(storyboard_id: str) -> None:
    """バックグラウンドで Claude API を呼び、Storyboard を更新する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            storyboard = await db.get(Storyboard, storyboard_id)
            if storyboard is None:
                logger.error("run_storyboard_generation: storyboard %s not found", storyboard_id)
                return

            project = await db.get(Project, storyboard.project_id)
            spec_result = await db.execute(
                select(VideoSpec).where(VideoSpec.project_id == storyboard.project_id)
            )
            spec = spec_result.scalar_one_or_none()

            structure = await db.get(Structure, storyboard.structure_id)
            if structure is None:
                raise ValueError("元の Structure が見つかりません")

            ai_result = await ai_service.generate_storyboard(project, spec, structure.scenes)

            merged_scenes = _validate_and_merge_storyboard_scenes(
                ai_result.get("scenes"), structure.scenes
            )

            storyboard.scenes = merged_scenes
            storyboard.status = StoryboardStatus.completed
            storyboard.generated_at = datetime.now(timezone.utc)
            _advance_project_status(project, ProjectStatus.storyboard)

            await db.commit()
        except Exception as e:
            logger.exception("run_storyboard_generation failed for storyboard %s", storyboard_id)
            await db.rollback()
            storyboard = await db.get(Storyboard, storyboard_id)
            if storyboard is not None:
                storyboard.status = StoryboardStatus.failed
                storyboard.error_message = str(e)
                await db.commit()


@router.get("/storyboard", response_model=StoryboardResponse)
async def get_storyboard(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新の Storyboard を取得する（version 降順で最初の1件）。なければ 404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Storyboard)
        .where(Storyboard.project_id == project.id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    storyboard = result.scalar_one_or_none()
    if storyboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found",
        )
    return StoryboardResponse.model_validate(storyboard)


@router.post("/storyboard/approve", response_model=StoryboardResponse)
async def approve_storyboard(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 Storyboard を承認し、プロジェクト status を 'shooting' に更新する。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Storyboard)
        .where(Storyboard.project_id == project.id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    storyboard = result.scalar_one_or_none()
    if storyboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found",
        )
    if storyboard.status != StoryboardStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storyboard がまだ生成中、または生成に失敗しています。",
        )

    storyboard.approved_at = datetime.now(timezone.utc)
    _advance_project_status(project, ProjectStatus.shooting)

    await db.flush()
    await db.refresh(storyboard)
    return StoryboardResponse.model_validate(storyboard)


# ---------------------------------------------------------------------------
# Storyboard revision endpoints (承認後のフィードバックによる再生成)
# ---------------------------------------------------------------------------


@router.post("/storyboard/revise", response_model=StoryboardResponse, status_code=202)
async def revise_storyboard(
    project_id: str,
    request: StoryboardReviseRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """承認済みの最新 Storyboard に対する修正指示から、改訂版の生成をバックグラウンドで開始する。

    結果は GET /storyboard でポーリングする。
    """
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Storyboard)
        .where(Storyboard.project_id == project.id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found",
        )
    if latest.status == StoryboardStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    if latest.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="承認済みのStoryboardがありません。先に絵コンテを承認してください。",
        )

    storyboard = Storyboard(
        project_id=project.id,
        structure_id=latest.structure_id,
        scenes=[],
        version=latest.version + 1,
        status=StoryboardStatus.pending,
        human_feedback=request.feedback,
        based_on_storyboard_id=latest.id,
    )
    db.add(storyboard)
    await db.flush()
    await db.refresh(storyboard)

    background_tasks.add_task(run_storyboard_revision, storyboard.id)

    return StoryboardResponse.model_validate(storyboard)


async def run_storyboard_revision(storyboard_id: str) -> None:
    """バックグラウンドで Claude API を呼び、修正指示を反映した改訂版 Storyboard を生成する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            storyboard = await db.get(Storyboard, storyboard_id)
            if storyboard is None:
                logger.error("run_storyboard_revision: storyboard %s not found", storyboard_id)
                return

            project = await db.get(Project, storyboard.project_id)
            spec_result = await db.execute(
                select(VideoSpec).where(VideoSpec.project_id == storyboard.project_id)
            )
            spec = spec_result.scalar_one_or_none()

            structure = await db.get(Structure, storyboard.structure_id)
            if structure is None:
                raise ValueError("元の Structure が見つかりません")

            base = await db.get(Storyboard, storyboard.based_on_storyboard_id)
            if base is None:
                raise ValueError("改訂元の Storyboard が見つかりません")

            ai_result = await ai_service.revise_storyboard(
                project, spec, structure.scenes, base.scenes, storyboard.human_feedback
            )

            merged_scenes = _validate_and_merge_storyboard_scenes(
                ai_result.get("scenes"), structure.scenes
            )

            storyboard.scenes = merged_scenes
            storyboard.status = StoryboardStatus.completed
            storyboard.generated_at = datetime.now(timezone.utc)
            _advance_project_status(project, ProjectStatus.storyboard)

            await db.commit()
        except Exception as e:
            logger.exception("run_storyboard_revision failed for storyboard %s", storyboard_id)
            await db.rollback()
            storyboard = await db.get(Storyboard, storyboard_id)
            if storyboard is not None:
                storyboard.status = StoryboardStatus.failed
                storyboard.error_message = str(e)
                await db.commit()
