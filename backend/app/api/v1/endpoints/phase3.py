import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.api.v1.endpoints._common import _advance_project_status, _get_project_for_user
from app.models.project import Project, ProjectStatus
from app.models.shooting_list import ShootingList, ShootingListStatus
from app.models.storyboard import Storyboard, StoryboardStatus
from app.models.user import User
from app.models.video_spec import VideoSpec
from app.schemas.shooting_list import (
    ShootingListShotAI,
    ShootingListShotToggleRequest,
    ShootingListResponse,
)
from app.services import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)

_SHOT_CATEGORY_LABELS: dict[str, str] = {
    "exterior": "外観",
    "people": "人物",
    "product": "商品",
    "broll": "Bロール",
    "other": "その他",
}


# ---------------------------------------------------------------------------
# ShootingList endpoints
# ---------------------------------------------------------------------------


@router.post("/shooting-list/generate", response_model=ShootingListResponse, status_code=202)
async def generate_shooting_list(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """承認済みの Storyboard から撮影リスト生成をバックグラウンドで開始する。結果は GET /shooting-list でポーリングする。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    storyboard_result = await db.execute(
        select(Storyboard)
        .where(Storyboard.project_id == project.id)
        .order_by(Storyboard.version.desc())
        .limit(1)
    )
    storyboard = storyboard_result.scalar_one_or_none()
    if storyboard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storyboard not found",
        )
    if storyboard.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="承認済みのStoryboardがありません。先に絵コンテを承認してください。",
        )

    latest_result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    if latest is not None and latest.status == ShootingListStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    next_version = (latest.version + 1) if latest else 1

    shooting_list = ShootingList(
        project_id=project.id,
        storyboard_id=storyboard.id,
        shots=[],
        version=next_version,
        status=ShootingListStatus.pending,
    )
    db.add(shooting_list)
    await db.flush()
    await db.refresh(shooting_list)

    background_tasks.add_task(run_shooting_list_generation, shooting_list.id)

    return ShootingListResponse.model_validate(shooting_list)


def _validate_and_merge_shooting_list_shots(raw_shots, storyboard_scenes: list) -> list[dict]:
    """AIの出力形状を検証し、cut_number/completedを付与した最終的なshotsリストを返す。

    オール・オア・ナッシング: shot の scene_number 集合が Storyboard のシーン番号
    集合と完全一致（カバレッジ一致。1シーンに複数shotは許容）しない、あるいは
    いずれかの形が壊れていれば ValueError を投げる（呼び出し側で failed へ落とす
    ことを想定）。
    """
    if not isinstance(raw_shots, list) or len(raw_shots) == 0:
        raise ValueError("AI応答に shots 配列がありません")

    expected_numbers = {s["scene_number"] for s in storyboard_scenes}
    got_numbers = {
        item.get("scene_number") if isinstance(item, dict) else None
        for item in raw_shots
    }
    if got_numbers != expected_numbers:
        raise ValueError(
            f"AI応答の scene_number が絵コンテのシーン番号と一致しません"
            f"（期待: {sorted(expected_numbers)}, 実際: {sorted(n for n in got_numbers if n is not None)}）"
        )

    validated = [ShootingListShotAI.model_validate(item).model_dump() for item in raw_shots]
    validated.sort(key=lambda item: item["scene_number"])

    merged_shots = []
    for cut_number, shot in enumerate(validated, start=1):
        merged_shots.append(
            {
                "cut_number": cut_number,
                "scene_number": shot["scene_number"],
                "category": shot["category"],
                "title": shot["title"],
                "location": shot["location"],
                "equipment": shot["equipment"],
                "talent_props": shot["talent_props"],
                "notes": shot["notes"],
                "completed": False,
            }
        )

    return merged_shots


async def run_shooting_list_generation(shooting_list_id: str) -> None:
    """バックグラウンドで Claude API を呼び、ShootingList を更新する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            shooting_list = await db.get(ShootingList, shooting_list_id)
            if shooting_list is None:
                logger.error("run_shooting_list_generation: shooting_list %s not found", shooting_list_id)
                return

            project = await db.get(Project, shooting_list.project_id)
            spec_result = await db.execute(
                select(VideoSpec).where(VideoSpec.project_id == shooting_list.project_id)
            )
            spec = spec_result.scalar_one_or_none()

            storyboard = await db.get(Storyboard, shooting_list.storyboard_id)
            if storyboard is None:
                raise ValueError("元の Storyboard が見つかりません")

            ai_result = await ai_service.generate_shooting_list(project, spec, storyboard.scenes)

            merged_shots = _validate_and_merge_shooting_list_shots(
                ai_result.get("shots"), storyboard.scenes
            )

            shooting_list.shots = merged_shots
            shooting_list.status = ShootingListStatus.completed
            shooting_list.generated_at = datetime.now(timezone.utc)
            _advance_project_status(project, ProjectStatus.shooting)

            await db.commit()
        except Exception as e:
            logger.exception("run_shooting_list_generation failed for shooting_list %s", shooting_list_id)
            await db.rollback()
            shooting_list = await db.get(ShootingList, shooting_list_id)
            if shooting_list is not None:
                shooting_list.status = ShootingListStatus.failed
                shooting_list.error_message = str(e)
                await db.commit()


@router.get("/shooting-list", response_model=ShootingListResponse)
async def get_shooting_list(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新の ShootingList を取得する（version 降順で最初の1件）。なければ 404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    shooting_list = result.scalar_one_or_none()
    if shooting_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ShootingList not found",
        )
    return ShootingListResponse.model_validate(shooting_list)


@router.get("/shooting-list/export")
async def export_shooting_list_csv(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 ShootingList を CSV（UTF-8 BOM付き）でダウンロードする。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    shooting_list = result.scalar_one_or_none()
    if shooting_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ShootingList not found",
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["カテゴリ", "ショット番号", "内容", "チェック状態"])
    for shot in shooting_list.shots:
        writer.writerow(
            [
                _SHOT_CATEGORY_LABELS.get(shot["category"], shot["category"]),
                shot["cut_number"],
                shot["title"],
                "済" if shot["completed"] else "未",
            ]
        )

    csv_bytes = buffer.getvalue().encode("utf-8-sig")

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="shooting_list.csv"'},
    )


@router.post("/shooting-list/approve", response_model=ShootingListResponse)
async def approve_shooting_list(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 ShootingList を承認し、プロジェクト status を 'upload' に更新する。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    shooting_list = result.scalar_one_or_none()
    if shooting_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ShootingList not found",
        )
    if shooting_list.status != ShootingListStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ShootingList がまだ生成中、または生成に失敗しています。",
        )

    shooting_list.approved_at = datetime.now(timezone.utc)
    _advance_project_status(project, ProjectStatus.upload)

    await db.flush()
    await db.refresh(shooting_list)
    return ShootingListResponse.model_validate(shooting_list)


@router.patch("/shooting-list/shots/{cut_number}", response_model=ShootingListResponse)
async def toggle_shooting_list_shot(
    project_id: str,
    cut_number: int,
    request: ShootingListShotToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 ShootingList の指定 cut_number の撮影完了フラグを更新する。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    shooting_list = result.scalar_one_or_none()
    if shooting_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ShootingList not found",
        )
    if shooting_list.status != ShootingListStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ShootingList がまだ生成中、または生成に失敗しています。",
        )

    if not any(shot["cut_number"] == cut_number for shot in shooting_list.shots):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"cut_number {cut_number} は見つかりません。",
        )

    new_shots = [
        {**shot, "completed": request.completed} if shot["cut_number"] == cut_number else shot
        for shot in shooting_list.shots
    ]
    shooting_list.shots = new_shots

    await db.flush()
    await db.refresh(shooting_list)
    return ShootingListResponse.model_validate(shooting_list)
