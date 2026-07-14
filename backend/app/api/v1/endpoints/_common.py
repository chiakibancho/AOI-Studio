from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.models.user import User


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


_PROJECT_STATUS_ORDER = list(ProjectStatus)  # 宣言順がフェーズの進行順


def _advance_project_status(project: Project, target: ProjectStatus) -> None:
    """project.status を target に進める。target が現在のフェーズより手前（または同じ）なら何もしない。

    承認後に再生成/改訂しても project.status がフェーズを後退しないようにするためのガード。
    """
    if _PROJECT_STATUS_ORDER.index(target) > _PROJECT_STATUS_ORDER.index(project.status):
        project.status = target
