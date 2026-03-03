"""
Storage upload and proxy router.
- Upload: proxies to storage_service; requires Admin/Super Admin.
- GET /storage/{path}: proxies files through web_service (no direct access to storage_service).
- Legacy /media/* aliases are kept for backward compatibility.
"""

import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import httpx

from api.dependencies import get_current_user
from shared.clients.database_client import db_client
from shared.clients.media_client import media_client
from shared.constants import Roles, StorageFileCategory
from shared.schemas.storage_file import StorageFileSchema
from shared.utils.media_utils import normalize_public_api_base

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Storage"])

STORAGE_SERVICE_URL = (
    os.getenv("STORAGE_SERVICE_HTTP_URL")
    or os.getenv("MEDIA_SERVICE_HTTP_URL", "http://127.0.0.1:8004")
).rstrip("/")
PUBLIC_API_BASE = normalize_public_api_base(os.getenv("PUBLIC_API_BASE_URL", ""))
if not PUBLIC_API_BASE:
    PUBLIC_API_BASE = normalize_public_api_base(os.getenv("NEXT_PUBLIC_API_URL", ""))


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
    Proxy files through web_service. Fetches from storage_service and streams to client.
    Public access (no auth required) for viewing/downloading files.
    """
    if not file_path or ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = file_path.lstrip("/")
    if path.startswith("media/"):
        path = path[6:].lstrip("/")
    if path.startswith("storage/"):
        path = path[8:].lstrip("/")
    if not path or not path.split("/")[-1]:
        raise HTTPException(status_code=400, detail="Invalid path")
    storage_url = f"{STORAGE_SERVICE_URL}/storage/{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(storage_url)
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="File not found")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Storage service error")
            content = resp.content
            content_type = resp.headers.get(
                "content-type", "application/octet-stream"
            )
            return StreamingResponse(
                iter([content]),
                media_type=content_type,
                headers={"Content-Length": str(len(content))},
            )
    except httpx.RequestError as e:
        logger.error(f"Storage proxy error for {path}: {e}")
        raise HTTPException(status_code=502, detail="Storage service unavailable")


@router.get("/storage/{file_path:path}")
async def serve_storage(file_path: str):
    return await _serve_file(file_path)


@router.get("/media/{file_path:path}")
async def serve_media(file_path: str):
    return await _serve_file(file_path)


async def _upload_file(
    *,
    file: UploadFile,
    category: str,
):
    """
    Upload a file to storage. Returns path and public URL (via web_service).
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
    except Exception as e:
        logger.error(f"Storage upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Ошибка загрузки файла")

    path = result.get("path", "")
    if path:
        if PUBLIC_API_BASE:
            result["url"] = f"{PUBLIC_API_BASE}/storage/{path}"
        else:
            result["url"] = f"/api/v1/storage/{path}"
        try:
            reg_resp = await db_client.storage_file.register_upload(
                storage_path=path,
                public_url=result["url"],
                original_name=result.get("original_name") or file.filename or path,
                content_type=result.get("content_type") or file.content_type,
                size_bytes=int(result.get("size_bytes") or len(content)),
                extension=result.get("extension"),
                kind=result.get("kind"),
                category=category or StorageFileCategory.DEFAULT,
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
                await media_client.delete(path)
            except Exception:
                logger.warning("Failed to rollback file %s after registry error", path, exc_info=True)
            raise HTTPException(status_code=502, detail="Ошибка регистрации файла")
    return result


@router.post("/storage/upload")
async def upload_storage(
    file: UploadFile = File(...),
    category: str = Form(StorageFileCategory.DEFAULT),
    _: dict = Depends(_require_admin),
):
    return await _upload_file(file=file, category=category)


@router.post("/media/upload")
async def upload_media(
    file: UploadFile = File(...),
    category: str = Form(StorageFileCategory.DEFAULT),
    _: dict = Depends(_require_admin),
):
    return await _upload_file(file=file, category=category)
