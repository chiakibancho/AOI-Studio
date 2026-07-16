import csv
import io
import logging
import mimetypes
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.core.config import MEDIA_ROOT, settings
from app.api.v1.endpoints._common import _advance_project_status, _get_project_for_user
from app.models.character import Character, CharacterStatus
from app.models.project import Project, ProjectStatus
from app.models.shooting_list import ShootingList, ShootingListStatus
from app.models.shot_image import ShotImage, ShotImageStatus
from app.models.storyboard import Storyboard, StoryboardStatus
from app.models.user import User
from app.models.video_spec import VideoSpec
from app.schemas.shooting_list import (
    ShootingListShotAI,
    ShootingListShotToggleRequest,
    ShootingListResponse,
)
from app.schemas.shot_image import ShotImageGenerateRequest, ShotImageResponse
from app.services import ai_service, shot_prompt_service, together_ai_service

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


# ---------------------------------------------------------------------------
# Shot image generation（絵コンテイラスト）
# キャラクターバイブルの together_ai_service.generate_character_sheet_image をそのまま流用する。
# 承認フローは無く、生成完了したら即表示。
# ---------------------------------------------------------------------------

_SHOT_IMAGE_DIR = "shot_images"


async def _get_shot_and_shooting_list(
    project_id: str,
    cut_number: int,
    current_user: User,
    db: AsyncSession,
) -> tuple[Project, ShootingList, dict]:
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(ShootingList)
        .where(ShootingList.project_id == project.id)
        .order_by(ShootingList.version.desc())
        .limit(1)
    )
    shooting_list = result.scalar_one_or_none()
    if shooting_list is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ShootingList not found")

    shot = next((s for s in shooting_list.shots if s["cut_number"] == cut_number), None)
    if shot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"cut_number {cut_number} は見つかりません。",
        )
    return project, shooting_list, shot


@router.post(
    "/shooting-list/shots/{cut_number}/generate-image",
    response_model=ShotImageResponse,
    status_code=202,
)
async def generate_shot_image(
    project_id: str,
    cut_number: int,
    request: ShotImageGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """撮影リストの1ショットから絵コンテイラストをバックグラウンドで生成する（202）。

    結果は GET .../shots/{cut_number}/image-status でポーリングする。承認は不要で、
    生成完了後は即座に画像を利用できる。既存のショットに対する再実行は上書き生成する。
    """
    if not settings.TOGETHER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TOGETHER_API_KEY が設定されていません。",
        )

    project, shooting_list, _shot = await _get_shot_and_shooting_list(
        project_id, cut_number, current_user, db
    )

    existing_result = await db.execute(
        select(ShotImage).where(
            ShotImage.shooting_list_id == shooting_list.id,
            ShotImage.cut_number == cut_number,
        )
    )
    shot_image = existing_result.scalar_one_or_none()
    if shot_image is not None and shot_image.status == ShotImageStatus.generating:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )

    if shot_image is None:
        shot_image = ShotImage(
            project_id=project.id,
            shooting_list_id=shooting_list.id,
            cut_number=cut_number,
            status=ShotImageStatus.generating,
        )
        db.add(shot_image)
    else:
        shot_image.status = ShotImageStatus.generating
        shot_image.error_message = None

    await db.flush()
    await db.refresh(shot_image)

    background_tasks.add_task(
        run_shot_image_generation, shot_image.id, project.id, cut_number, request.style
    )

    return ShotImageResponse.model_validate(shot_image)


async def run_shot_image_generation(
    shot_image_id: str, project_id: str, cut_number: int, style: str
) -> None:
    """バックグラウンドでFLUXプロンプトを組み立て、Together AIで絵コンテイラストを生成する。"""
    async with AsyncSessionLocal() as db:
        try:
            shot_image = await db.get(ShotImage, shot_image_id)
            if shot_image is None:
                logger.error("run_shot_image_generation: shot_image %s not found", shot_image_id)
                return

            shooting_list = await db.get(ShootingList, shot_image.shooting_list_id)
            if shooting_list is None:
                raise ValueError("元の ShootingList が見つかりません")
            shot = next((s for s in shooting_list.shots if s["cut_number"] == cut_number), None)
            if shot is None:
                raise ValueError(f"cut_number {cut_number} は見つかりません")

            character_result = await db.execute(
                select(Character)
                .where(
                    Character.project_id == project_id,
                    Character.status == CharacterStatus.approved,
                )
                .order_by(Character.approved_at.desc())
                .limit(1)
            )
            character = character_result.scalar_one_or_none()
            character_prompt = character.prompt if character else ""

            prompt = shot_prompt_service.generate_flux_prompt(shot, character_prompt, style)

            image_bytes = await together_ai_service.generate_character_sheet_image(prompt)
            ext = together_ai_service.sniff_image_extension(image_bytes)

            image_dir = MEDIA_ROOT / _SHOT_IMAGE_DIR
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"{shot_image.id}{ext}"
            image_path.write_bytes(image_bytes)

            shot_image.image_path = f"{_SHOT_IMAGE_DIR}/{shot_image.id}{ext}"
            shot_image.status = ShotImageStatus.generated
            shot_image.updated_at = datetime.now(timezone.utc)

            await db.commit()
        except Exception as e:
            logger.exception("run_shot_image_generation failed for shot_image %s", shot_image_id)
            await db.rollback()
            shot_image = await db.get(ShotImage, shot_image_id)
            if shot_image is not None:
                shot_image.status = ShotImageStatus.failed
                shot_image.error_message = str(e)
                await db.commit()


@router.get("/shooting-list/shots/{cut_number}/image-status", response_model=ShotImageResponse)
async def get_shot_image_status(
    project_id: str,
    cut_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """指定ショットの絵コンテイラスト生成状況を取得する（ポーリング用）。未生成なら404。"""
    _project, shooting_list, _shot = await _get_shot_and_shooting_list(
        project_id, cut_number, current_user, db
    )

    result = await db.execute(
        select(ShotImage).where(
            ShotImage.shooting_list_id == shooting_list.id,
            ShotImage.cut_number == cut_number,
        )
    )
    shot_image = result.scalar_one_or_none()
    if shot_image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ShotImage not found")
    return ShotImageResponse.model_validate(shot_image)


@router.get("/shooting-list/shots/{cut_number}/image")
async def get_shot_image(
    project_id: str,
    cut_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成済み絵コンテイラスト画像をバイナリで配信する（認証必須）。"""
    _project, shooting_list, _shot = await _get_shot_and_shooting_list(
        project_id, cut_number, current_user, db
    )

    result = await db.execute(
        select(ShotImage).where(
            ShotImage.shooting_list_id == shooting_list.id,
            ShotImage.cut_number == cut_number,
        )
    )
    shot_image = result.scalar_one_or_none()
    if (
        shot_image is None
        or shot_image.image_path is None
        or shot_image.status != ShotImageStatus.generated
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shot image not found")

    image_path = MEDIA_ROOT / shot_image.image_path
    if not image_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shot image not found")

    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    return FileResponse(image_path, media_type=media_type)
