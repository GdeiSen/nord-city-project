"""
Storage router.
- Upload: creates/finalizes presigned uploads; requires Admin/Super Admin.
- GET /storage/{path}: validates the file and redirects to a short-lived MinIO URL.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.dependencies import get_current_user
from shared.clients.database_client import db_client
from shared.clients.storage_client import storage_client
from shared.constants import Roles, StorageFileCategory
from shared.schemas.storage_file import StorageFileSchema
from shared.utils.storage_utils import normalize_public_api_base

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Storage"])
PUBLIC_API_BASE = normalize_public_api_base(os.getenv("PUBLIC_API_BASE_URL", ""))
if not PUBLIC_API_BASE:
    PUBLIC_API_BASE = normalize_public_api_base(os.getenv("NEXT_PUBLIC_API_URL", ""))


class StorageUploadInitRequest(BaseModel):
    filename: str
    content_type: str | None = None
    size_bytes: int = 0
    category: str = StorageFileCategory.DEFAULT


class StorageUploadCompleteRequest(BaseModel):
    path: str
    original_name: str
    content_type: str | None = None
    category: str = StorageFileCategory.DEFAULT


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure user is Admin or Super Admin."""
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


async def _serve_file(file_path: str):
    """
    Validate file registration and redirect the client to a short-lived
    signed MinIO download URL so bytes are read directly from MinIO.
    """
    if not file_path or ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = file_path.lstrip("/")
    if path.startswith("storage/"):
        path = path[8:].lstrip("/")
    if not path or not path.split("/")[-1]:
        raise HTTPException(status_code=400, detail="Invalid path")

    try:
        registry_response = await db_client.storage_file.find_by_path(
            storage_path=path,
            model_class=StorageFileSchema,
        )
        if not registry_response.get("success"):
            raise HTTPException(status_code=502, detail="Storage registry unavailable")
        if registry_response.get("data") is None:
            raise HTTPException(status_code=404, detail="File not found")

        session = await storage_client.create_download_session(path=path)
    except HTTPException:
        raise
    except Exception as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(status_code=404, detail="File not found")
        logger.error("Storage redirect generation failed for %s: %s", path, exc, exc_info=True)
        raise HTTPException(status_code=502, detail="Storage service unavailable")

    download_url = str(session.get("download_url") or "").strip()
    if not download_url:
        raise HTTPException(status_code=502, detail="Storage service returned invalid download URL")

    return RedirectResponse(
        url=download_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/storage/{file_path:path}")
async def serve_storage(file_path: str):
    return await _serve_file(file_path)


async def _create_presigned_upload(
    *,
    payload: StorageUploadInitRequest,
) -> dict:
    if not payload.filename or not payload.filename.strip():
        raise HTTPException(status_code=400, detail="Имя файла обязательно")

    try:
        session = await storage_client.create_upload_session(
            filename=payload.filename.strip(),
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
    except Exception as e:
        logger.error("Failed to create presigned upload session: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="Не удалось создать ссылку загрузки")

    return {
        "path": session.get("path"),
        "upload_url": session.get("upload_url"),
        "method": session.get("method", "PUT"),
        "headers": session.get("headers") or {},
        "content_type": session.get("content_type"),
        "expires_in": session.get("expires_in"),
        "original_name": payload.filename.strip(),
        "category": payload.category or StorageFileCategory.DEFAULT,
    }


async def _complete_presigned_upload(
    *,
    payload: StorageUploadCompleteRequest,
) -> dict:
    try:
        result = await storage_client.complete_upload(
            path=payload.path,
            original_name=payload.original_name,
            content_type=payload.content_type,
        )
    except Exception as e:
        logger.error("Failed to finalize uploaded file %s: %s", payload.path, e, exc_info=True)
        raise HTTPException(status_code=502, detail="Не удалось завершить загрузку файла")

    path = result.get("path", "")
    if not path:
        raise HTTPException(status_code=502, detail="Storage service returned invalid path")

    if PUBLIC_API_BASE:
        result["url"] = f"{PUBLIC_API_BASE}/storage/{path}"
    else:
        result["url"] = f"/api/v1/storage/{path}"

    try:
        reg_resp = await db_client.storage_file.register_upload(
            storage_path=path,
            public_url=result["url"],
            original_name=result.get("original_name") or payload.original_name or path,
            content_type=result.get("content_type") or payload.content_type,
            size_bytes=int(result.get("size_bytes") or 0),
            extension=result.get("extension"),
            kind=result.get("kind"),
            category=payload.category or StorageFileCategory.DEFAULT,
            model_class=StorageFileSchema,
        )
        if not reg_resp.get("success"):
            raise RuntimeError(reg_resp.get("error", "registry_failed"))
        registry_item = reg_resp.get("data")
        if registry_item is not None:
            result["file_id"] = registry_item.id
    except Exception as e:
        logger.error("Storage registry failed for %s: %s", path, e, exc_info=True)
        try:
            await storage_client.delete(path)
        except Exception:
            logger.warning("Failed to rollback file %s after registry error", path, exc_info=True)
        raise HTTPException(status_code=502, detail="Ошибка регистрации файла")

    return result


@router.post("/storage/uploads/init")
async def init_storage_upload(
    payload: StorageUploadInitRequest,
    _: dict = Depends(_require_admin),
):
    return await _create_presigned_upload(payload=payload)


@router.post("/storage/uploads/complete")
async def complete_storage_upload(
    payload: StorageUploadCompleteRequest,
    _: dict = Depends(_require_admin),
):
    return await _complete_presigned_upload(payload=payload)
