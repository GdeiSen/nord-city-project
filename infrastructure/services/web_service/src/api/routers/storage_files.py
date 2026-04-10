from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_current_user
from api.helpers.paginated_list import create_paginated_list_handler
from api.schemas.common import PaginatedResponse
from api.schemas.storage_files import StorageFileResponse
from shared.clients.database_client import db_client
from shared.constants import Roles
from shared.schemas.storage_file import StorageFileSchema

router = APIRouter(prefix="/storage-files", tags=["Storage Files"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


get_storage_files = create_paginated_list_handler(
    db_client.storage_file,
    model_class=StorageFileSchema,
    enricher=None,
    response_schema=StorageFileResponse,
    entity_label="storage files",
)
router.get(
    "/",
    response_model=PaginatedResponse[StorageFileResponse],
    dependencies=[Depends(_require_admin)],
)(get_storage_files)


@router.get("/{entity_id}", response_model=StorageFileResponse)
async def get_storage_file_by_id(
    entity_id: int,
    _: dict = Depends(_require_admin),
):
    response = await db_client.storage_file.get_by_id(
        entity_id=entity_id,
        model_class=StorageFileSchema,
    )
    if not response.get("success"):
        error = response.get("error", "Storage file not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage file not found")
    return StorageFileResponse(**response["data"].model_dump())
