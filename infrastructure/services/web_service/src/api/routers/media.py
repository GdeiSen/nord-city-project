"""
Media upload router.
Proxies uploads to media_service; requires Admin/Super Admin authentication.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import get_current_user
from shared.clients.media_client import media_client
from shared.constants import Roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure user is Admin or Super Admin."""
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    _: dict = Depends(_require_admin),
):
    """
    Upload a file to media storage. Returns path and public URL.
    Requires Admin or Super Admin.
    """
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл")

    if not content:
        raise HTTPException(status_code=400, detail="Пустой файл")

    try:
        result = await media_client.upload(
            file_content=content,
            filename=file.filename or "file",
            content_type=file.content_type,
        )
        return result
    except Exception as e:
        logger.error(f"Media upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Ошибка загрузки медиа")
