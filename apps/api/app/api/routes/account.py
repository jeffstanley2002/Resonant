from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import AuthUser, require_user
from app.schemas import DataDeletionResponse
from app.services.storage import delete_user_data

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("/data", response_model=DataDeletionResponse)
async def delete_account_data(user: AuthUser = Depends(require_user)) -> DataDeletionResponse:
    deleted_tables = await delete_user_data(user_id=user.id)
    return DataDeletionResponse(deleted_tables=deleted_tables)
