from fastapi import APIRouter

from app.api.v1.endpoints import auth, projects, phase1

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(
    phase1.router,
    prefix="/projects/{project_id}",
    tags=["phase1"],
)
