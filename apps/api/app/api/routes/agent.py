from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, require_user
from app.schemas import MatchRequest, MatchResponse
from app.services.agent import ResumeAnalysisNotFound, run_match_workflow

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/matches", response_model=MatchResponse)
async def create_matches(
    request: MatchRequest,
    user: AuthUser = Depends(require_user),
) -> MatchResponse:
    try:
        return await run_match_workflow(user_id=user.id, request=request)
    except ResumeAnalysisNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume analysis was not found for this account",
        ) from exc
