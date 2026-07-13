import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.spec_draft import SpecDraft, SpecDraftStatus
from app.models.structure import Structure, StructureStatus
from app.models.user import User
from app.models.video_spec import VideoSpec
from app.schemas.spec_draft import SpecDraftGenerateRequest, SpecDraftResponse
from app.schemas.structure import StructureOption, StructureReviseRequest, StructureResponse
from app.schemas.video_spec import VideoSpecCreate, VideoSpecResponse
from app.services import ai_service

router = APIRouter()
logger = logging.getLogger(__name__)


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


async def _upsert_video_spec_fields(
    db: AsyncSession,
    project: Project,
    data: VideoSpecCreate,
) -> VideoSpec:
    """VideoSpec を作成 or 更新して flush する（commit はしない）。"""
    result = await db.execute(
        select(VideoSpec).where(VideoSpec.project_id == project.id)
    )
    spec = result.scalar_one_or_none()

    if spec is None:
        spec = VideoSpec(
            project_id=project.id,
            duration_sec=data.duration_sec,
            target_audience=data.target_audience,
            message=data.message,
            mood=data.mood,
            style_notes=data.style_notes,
            reference_urls=data.reference_urls,
        )
        db.add(spec)
    else:
        spec.duration_sec = data.duration_sec
        spec.target_audience = data.target_audience
        spec.message = data.message
        spec.mood = data.mood
        spec.style_notes = data.style_notes
        spec.reference_urls = data.reference_urls
        spec.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(spec)
    return spec


_PROJECT_STATUS_ORDER = list(ProjectStatus)  # 宣言順がフェーズの進行順


def _advance_project_status(project: Project, target: ProjectStatus) -> None:
    """project.status を target に進める。target が現在のフェーズより手前（または同じ）なら何もしない。

    承認後に再生成/改訂しても project.status がフェーズを後退しないようにするためのガード。
    """
    if _PROJECT_STATUS_ORDER.index(target) > _PROJECT_STATUS_ORDER.index(project.status):
        project.status = target


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
    spec = await _upsert_video_spec_fields(db, project, request)
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
# SpecDraft endpoints
# ---------------------------------------------------------------------------


@router.post("/spec-draft/generate", response_model=SpecDraftResponse, status_code=202)
async def generate_spec_draft(
    project_id: str,
    request: SpecDraftGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """自然言語入力から AI による SpecDraft 生成をバックグラウンドで開始する。結果は GET /spec-draft でポーリングする。"""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    # 既存の最新バージョンを確認
    latest_result = await db.execute(
        select(SpecDraft)
        .where(SpecDraft.project_id == project.id)
        .order_by(SpecDraft.version.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    if latest is not None and latest.status == SpecDraftStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    next_version = (latest.version + 1) if latest else 1

    # pending 状態のレコードを即座に作成し、生成はバックグラウンドに委譲する
    draft = SpecDraft(
        project_id=project.id,
        raw_input=request.raw_input,
        version=next_version,
        status=SpecDraftStatus.pending,
    )
    db.add(draft)
    await db.flush()
    await db.refresh(draft)

    background_tasks.add_task(run_spec_draft_generation, draft.id)

    return SpecDraftResponse.model_validate(draft)


async def run_spec_draft_generation(draft_id: str) -> None:
    """バックグラウンドで Claude API を呼び、SpecDraft を更新する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            draft = await db.get(SpecDraft, draft_id)
            if draft is None:
                logger.error("run_spec_draft_generation: draft %s not found", draft_id)
                return

            project = await db.get(Project, draft.project_id)

            ai_result = await ai_service.analyze_spec(project, draft.raw_input)

            # AIの出力形状をここで検証する。壊れていればここで例外→failedへ。
            spec_fields = VideoSpecCreate.model_validate(
                {k: v for k, v in ai_result.items() if k != "rationale"}
            )

            draft.duration_sec = spec_fields.duration_sec
            draft.target_audience = spec_fields.target_audience
            draft.message = spec_fields.message
            draft.mood = spec_fields.mood
            draft.style_notes = spec_fields.style_notes
            draft.reference_urls = spec_fields.reference_urls
            draft.rationale = ai_result.get("rationale", "")
            draft.status = SpecDraftStatus.completed
            draft.generated_at = datetime.now(timezone.utc)

            await db.commit()
        except Exception as e:
            logger.exception("run_spec_draft_generation failed for draft %s", draft_id)
            await db.rollback()
            draft = await db.get(SpecDraft, draft_id)
            if draft is not None:
                draft.status = SpecDraftStatus.failed
                draft.error_message = str(e)
                await db.commit()


@router.get("/spec-draft", response_model=SpecDraftResponse)
async def get_spec_draft(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新の SpecDraft を取得する（version 降順で最初の1件）。なければ 404。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(SpecDraft)
        .where(SpecDraft.project_id == project.id)
        .order_by(SpecDraft.version.desc())
        .limit(1)
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SpecDraft not found",
        )
    return SpecDraftResponse.model_validate(draft)


@router.post("/spec-draft/approve", response_model=VideoSpecResponse)
async def approve_spec_draft(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 SpecDraft を承認し、その内容で VideoSpec を作成/更新する。"""
    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(SpecDraft)
        .where(SpecDraft.project_id == project.id)
        .order_by(SpecDraft.version.desc())
        .limit(1)
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SpecDraft not found",
        )
    if draft.status != SpecDraftStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SpecDraft がまだ生成中、または生成に失敗しています。",
        )

    spec_data = VideoSpecCreate(
        duration_sec=draft.duration_sec,
        target_audience=draft.target_audience,
        message=draft.message,
        mood=draft.mood,
        style_notes=draft.style_notes,
        reference_urls=draft.reference_urls,
    )
    spec = await _upsert_video_spec_fields(db, project, spec_data)

    draft.approved_at = datetime.now(timezone.utc)
    await db.flush()

    return VideoSpecResponse.model_validate(spec)


# ---------------------------------------------------------------------------
# Structure endpoints
# ---------------------------------------------------------------------------


@router.post("/structure/generate", response_model=StructureResponse, status_code=202)
async def generate_structure(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI による Structure 生成をバックグラウンドで開始する。結果は GET /structure でポーリングする。"""
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
    if latest is not None and latest.status == StructureStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    next_version = (latest.version + 1) if latest else 1

    # pending 状態のレコードを即座に作成し、生成はバックグラウンドに委譲する
    structure = Structure(
        project_id=project.id,
        scenes=[],
        rationale="",
        total_duration_sec=0,
        version=next_version,
        status=StructureStatus.pending,
    )
    db.add(structure)
    await db.flush()
    await db.refresh(structure)

    background_tasks.add_task(run_structure_generation, structure.id)

    return StructureResponse.model_validate(structure)


async def run_structure_generation(structure_id: str) -> None:
    """バックグラウンドで Claude API を呼び、Structure を更新する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            structure = await db.get(Structure, structure_id)
            if structure is None:
                logger.error("run_structure_generation: structure %s not found", structure_id)
                return

            project = await db.get(Project, structure.project_id)
            spec_result = await db.execute(
                select(VideoSpec).where(VideoSpec.project_id == structure.project_id)
            )
            spec = spec_result.scalar_one_or_none()

            ai_result = await ai_service.generate_structure(project, spec)

            # AIの出力形状をここで検証する。壊れていればここで例外→failedへ。
            # オール・オア・ナッシング: options が無い/3件でない/いずれかのscenesが壊れていれば
            # 生成全体を failed にする（部分的に有効な案だけ残すことはしない）。
            raw_options = ai_result.get("options")
            if not isinstance(raw_options, list):
                raise ValueError("AI応答に options 配列がありません")
            if len(raw_options) != 3:
                raise ValueError(
                    f"AI応答の案の数が不正です（期待: 3, 実際: {len(raw_options)}）"
                )
            validated_options = [
                StructureOption.model_validate(opt).model_dump() for opt in raw_options
            ]

            default_option = validated_options[0]
            structure.options = validated_options
            structure.scenes = default_option["scenes"]
            structure.rationale = default_option["rationale"]
            structure.total_duration_sec = default_option["total_duration_sec"]
            structure.status = StructureStatus.completed
            structure.generated_at = datetime.now(timezone.utc)
            _advance_project_status(project, ProjectStatus.structure)

            await db.commit()
        except Exception as e:
            logger.exception("run_structure_generation failed for structure %s", structure_id)
            await db.rollback()
            structure = await db.get(Structure, structure_id)
            if structure is not None:
                structure.status = StructureStatus.failed
                structure.error_message = str(e)
                await db.commit()


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
    option_index: int = Query(0, ge=0, le=2),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """最新 Structure を承認し、プロジェクト status を 'storyboard' に更新する。

    3案(options)が存在する場合は option_index で選んだ案をトップレベルの
    scenes/rationale/total_duration_sec に反映する。省略時は 0（デフォルトプレビュー
    として生成完了時に既にミラーされている案）が選ばれるため、既存の無パラメータ呼び出しと
    完全に後方互換になる。
    """
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
    if structure.status != StructureStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Structure がまだ生成中、または生成に失敗しています。",
        )

    if structure.options:
        if option_index >= len(structure.options):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な案です。",
            )
        chosen = structure.options[option_index]
        structure.scenes = chosen["scenes"]
        structure.rationale = chosen["rationale"]
        structure.total_duration_sec = chosen["total_duration_sec"]
        structure.selected_option_index = option_index

    structure.approved_at = datetime.now(timezone.utc)
    _advance_project_status(project, ProjectStatus.storyboard)

    await db.flush()
    await db.refresh(structure)
    return StructureResponse.model_validate(structure)


# ---------------------------------------------------------------------------
# Structure revision endpoints (承認後のフィードバックによる再生成)
# ---------------------------------------------------------------------------


@router.post("/structure/revise", response_model=StructureResponse, status_code=202)
async def revise_structure(
    project_id: str,
    request: StructureReviseRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """承認済みの最新 Structure に対する修正指示から、改訂版（1件）の生成をバックグラウンドで開始する。

    元の3案のうち承認された1案の内容のみを元に改訂する。結果は GET /structure でポーリングする。
    """
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ANTHROPIC_API_KEY が設定されていません。",
        )

    project = await _get_project_for_user(project_id, current_user, db)

    result = await db.execute(
        select(Structure)
        .where(Structure.project_id == project.id)
        .order_by(Structure.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure not found",
        )
    if latest.status == StructureStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="既に生成処理が進行中です。",
        )
    if latest.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="承認済みのStructureがありません。先に案を選んで承認してください。",
        )

    structure = Structure(
        project_id=project.id,
        scenes=[],
        rationale="",
        total_duration_sec=0,
        options=[],
        version=latest.version + 1,
        status=StructureStatus.pending,
        human_feedback=request.feedback,
        based_on_structure_id=latest.id,
    )
    db.add(structure)
    await db.flush()
    await db.refresh(structure)

    background_tasks.add_task(run_structure_revision, structure.id)

    return StructureResponse.model_validate(structure)


async def run_structure_revision(structure_id: str) -> None:
    """バックグラウンドで Claude API を呼び、修正指示を反映した改訂版 Structure を生成する。専用の DB セッションを使う。"""
    async with AsyncSessionLocal() as db:
        try:
            structure = await db.get(Structure, structure_id)
            if structure is None:
                logger.error("run_structure_revision: structure %s not found", structure_id)
                return

            project = await db.get(Project, structure.project_id)
            spec_result = await db.execute(
                select(VideoSpec).where(VideoSpec.project_id == structure.project_id)
            )
            spec = spec_result.scalar_one_or_none()

            base = await db.get(Structure, structure.based_on_structure_id)
            if base is None:
                raise ValueError("改訂元の Structure が見つかりません")

            ai_result = await ai_service.revise_structure(
                project, spec, base.scenes, base.rationale, structure.human_feedback
            )

            # AIの出力形状をここで検証する。壊れていればここで例外→failedへ。
            validated = StructureOption.model_validate(ai_result).model_dump()

            structure.scenes = validated["scenes"]
            structure.rationale = validated["rationale"]
            structure.total_duration_sec = validated["total_duration_sec"]
            structure.status = StructureStatus.completed
            structure.generated_at = datetime.now(timezone.utc)
            _advance_project_status(project, ProjectStatus.structure)

            await db.commit()
        except Exception as e:
            logger.exception("run_structure_revision failed for structure %s", structure_id)
            await db.rollback()
            structure = await db.get(Structure, structure_id)
            if structure is not None:
                structure.status = StructureStatus.failed
                structure.error_message = str(e)
                await db.commit()
