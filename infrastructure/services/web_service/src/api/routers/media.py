"""
Media upload and proxy router.
- Upload: proxies to media_service; requires Admin/Super Admin.
- GET /{path}: proxies media files through web_service (no direct access to media_service).
"""

import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import httpx

from api.dependencies import get_current_user
from shared.clients.media_client import media_client
from shared.constants import Roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["Media"])

MEDIA_SERVICE_URL = os.getenv("MEDIA_SERVICE_HTTP_URL", "http://127.0.0.1:8004").rstrip("/")
PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure user is Admin or Super Admin."""
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


@router.get("/{file_path:path}")
async def serve_media(file_path: str):
    """
    Proxy media files through web_service. Fetches from media_service and streams to client.
    Public access (no auth required) for viewing images.
    """
    if not file_path or ".." in file_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    path = file_path.lstrip("/")
    if path.startswith("media/"):
        path = path[6:].lstrip("/")
    if not path or not path.split("/")[-1]:
        raise HTTPException(status_code=400, detail="Invalid path")
    media_url = f"{MEDIA_SERVICE_URL}/media/{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", media_url) as resp:
                if resp.status_code == 404:
                    raise HTTPException(status_code=404, detail="File not found")
                if resp.status_code != 200:
                    raise HTTPException(status_code=502, detail="Media service error")
                content_type = resp.headers.get(
                    "content-type", "application/octet-stream"
                )
                content_length = resp.headers.get("content-length")
                headers = {}
                if content_length:
                    headers["Content-Length"] = content_length

                async def gen():
                    async for chunk in resp.aiter_bytes():
                        yield chunk

                return StreamingResponse(
                    gen(), media_type=content_type, headers=headers
                )
    except httpx.RequestError as e:
        logger.error(f"Media proxy error for {path}: {e}")
        raise HTTPException(status_code=502, detail="Media service unavailable")


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    _: dict = Depends(_require_admin),
):
    """
    Upload a file to media storage. Returns path and public URL (via web_service).
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
        logger.error(f"Media upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Ошибка загрузки медиа")

    path = result.get("path", "")
    if path:
        if PUBLIC_API_BASE:
            result["url"] = f"{PUBLIC_API_BASE}/media/{path}"
        else:
            result["url"] = f"/api/v1/media/{path}"
    return result
