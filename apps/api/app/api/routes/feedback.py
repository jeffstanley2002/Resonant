from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import AuthUser, require_user
from app.schemas import FeedbackRequest, FeedbackResponse
from app.services.storage import save_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user: AuthUser = Depends(require_user),
) -> FeedbackResponse:
    await save_feedback(user_id=user.id, request=request)
    return FeedbackResponse()
