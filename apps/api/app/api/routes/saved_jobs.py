from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import AuthUser, require_user
from app.schemas import SavedJob, SaveJobRequest
from app.services.storage import list_saved_jobs, save_job

router = APIRouter(prefix="/saved-jobs", tags=["saved jobs"])


@router.get("", response_model=list[SavedJob])
async def get_saved_jobs(user: AuthUser = Depends(require_user)) -> list[SavedJob]:
    return await list_saved_jobs(user_id=user.id)


@router.post("", response_model=SavedJob)
async def create_saved_job(
    request: SaveJobRequest,
    user: AuthUser = Depends(require_user),
) -> SavedJob:
    return await save_job(user_id=user.id, request=request)
