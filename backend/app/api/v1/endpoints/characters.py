import logging
import mimetypes
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MEDIA_ROOT, settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.api.v1.endpoints._common import _get_project_for_user
from app.models.character import Character, CharacterStatus
from app.models.user import User
from app.schemas.character import CharacterCreateRequest, CharacterResponse
from app.services import together_ai_service

router = APIRouter()
standalone_router = APIRouter()
logger = logging.getLogger(__name__)

_SHEET_DIR = "character_sheets"


async def _get_character_for_user(
    character_id: str,
    current_user: User,
    db: AsyncSession,
) -> Character:
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")

    # 所有権チェック（character -> project -> user）
    await _get_project_for_user(character.project_id, current_user, db)
    return character


# ---------------------------------------------------------------------------
# Project-scoped: create / list characters
# ---------------------------------------------------------------------------


@router.post("/characters", response_model=CharacterResponse, status_code=201)
async def create_character(
    project_id: str,
    request: CharacterCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """キャラクターを作成する（name + prompt）。prompt はFLUXにそのまま渡す全文テキスト。"""
    project = await _get_project_for_user(project_id, current_user, db)

    character = Character(
        project_id=project.id,
        name=request.name,
        prompt=request.prompt,
        status=CharacterStatus.draft,
    )
    db.add(character)
    await db.flush()
    await db.refresh(character)
    return CharacterResponse.model_validate(character)


@router.get("/characters", response_model=list[CharacterResponse])
async def list_characters(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """プロジェクトのキャラクター一覧を作成日時の昇順で返す。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Character).where(Character.project_id == project.id).order_by(Character.created_at)
    )
    characters = result.scalars().all()
    return [CharacterResponse.model_validate(c) for c in characters]


# ---------------------------------------------------------------------------
# Character-scoped: fetch / generate / approve / sheet image
# ---------------------------------------------------------------------------


@standalone_router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    character = await _get_character_for_user(character_id, current_user, db)
    return CharacterResponse.model_validate(character)


@standalone_router.post("/{character_id}/generate", response_model=CharacterResponse, status_code=202)
async def generate_character_sheet(
    character_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """モデルシート生成をバックグラウンドで開始する。結果は GET /characters/{id} でポーリングする。

    承認済みキャラクターは再生成不可。生成中の再実行は409。それ以外（draft/generated/failed）は
    generate の再実行で上書き生成する。
    """
    if not settings.TOGETHER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TOGETHER_API_KEY が設定されていません。",
        )

    character = await _get_character_for_user(character_id, current_user, db)

    if character.status == CharacterStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="承認済みのキャラクターは再生成できません。",
        )
    if character.status == CharacterStatus.generating:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )

    character.status = CharacterStatus.generating
    character.error_message = None
    await db.flush()
    await db.refresh(character)

    background_tasks.add_task(run_character_generation, character.id)

    return CharacterResponse.model_validate(character)


async def run_character_generation(character_id: str) -> None:
    """バックグラウンドで Together AI を呼び、モデルシート画像を生成してCharacterを更新する。"""
    async with AsyncSessionLocal() as db:
        try:
            character = await db.get(Character, character_id)
            if character is None:
                logger.error("run_character_generation: character %s not found", character_id)
                return

            image_bytes = await together_ai_service.generate_character_sheet_image(character.prompt)
            ext = together_ai_service.sniff_image_extension(image_bytes)

            sheet_dir = MEDIA_ROOT / _SHEET_DIR
            sheet_dir.mkdir(parents=True, exist_ok=True)
            image_path = sheet_dir / f"{character.id}{ext}"
            image_path.write_bytes(image_bytes)

            character.sheet_image_path = f"{_SHEET_DIR}/{character.id}{ext}"
            character.status = CharacterStatus.generated
            character.updated_at = datetime.now(timezone.utc)

            await db.commit()
        except Exception as e:
            logger.exception("run_character_generation failed for character %s", character_id)
            await db.rollback()
            character = await db.get(Character, character_id)
            if character is not None:
                character.status = CharacterStatus.failed
                character.error_message = str(e)
                await db.commit()


@standalone_router.get("/{character_id}/sheet-image")
async def get_character_sheet_image(
    character_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成済みモデルシート画像をバイナリで配信する（認証必須）。"""
    character = await _get_character_for_user(character_id, current_user, db)

    if character.sheet_image_path is None or character.status not in (
        CharacterStatus.generated,
        CharacterStatus.approved,
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet image not found")

    image_path = MEDIA_ROOT / character.sheet_image_path
    if not image_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet image not found")

    media_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    return FileResponse(image_path, media_type=media_type)


@standalone_router.post("/{character_id}/approve", response_model=CharacterResponse)
async def approve_character(
    character_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """生成済みモデルシートを承認する。承認後は再生成できなくなる。"""
    character = await _get_character_for_user(character_id, current_user, db)

    if character.status != CharacterStatus.generated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="モデルシートがまだ生成中、または生成に失敗しています。",
        )

    character.status = CharacterStatus.approved
    character.approved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(character)
    return CharacterResponse.model_validate(character)
