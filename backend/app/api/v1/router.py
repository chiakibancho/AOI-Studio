from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, phase1, phase2, phase3, music

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    phase1.router,
    prefix="/projects/{project_id}",
    tags=["phase1"],
)
api_router.include_router(
    phase2.router,
    prefix="/projects/{project_id}",
    tags=["phase2"],
)
api_router.include_router(
    phase3.router,
    prefix="/projects/{project_id}",
    tags=["phase3"],
)
api_router.include_router(
    music.router,
    prefix="/projects/{project_id}",
    tags=["music"],
)
