import io
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from telegram import InputFile

from shared.schemas import StorageFileSchema
from shared.utils.storage_utils import extract_storage_path, normalize_public_api_base, to_public_storage_url
from .base_service import BaseService

logger = logging.getLogger(__name__)


class MediaService(BaseService):
    """Service for adaptive Telegram media delivery and storage-file metadata caching."""

    async def initialize(self) -> None:
        logger.info("MediaService initialized")

    async def get_storage_file_telegram_file_id(self, storage_path: str | None) -> str | None:
        if not storage_path:
            return None
        try:
            response = await self.bot.managers.database.storage_file.find_by_path(
                storage_path=storage_path,
                model_class=StorageFileSchema,
            )
        except Exception:
            return None
        if not response.get("success"):
            return None
        data = response.get("data")
        meta: dict[str, Any] = {}
        if isinstance(data, dict):
            raw = data.get("meta")
            if isinstance(raw, dict):
                meta = raw
        else:
            raw = getattr(data, "meta", None)
            if isinstance(raw, dict):
                meta = raw
        telegram_file_id = str(meta.get("telegram_file_id") or "").strip()
        return telegram_file_id or None

    async def persist_storage_file_telegram_file_id(self, *, storage_path: str | None, telegram_file_id: str | None) -> None:
        if not storage_path:
            return
        try:
            await self.bot.managers.database.storage_file.merge_meta_by_path(
                storage_path=storage_path,
                meta_updates={"telegram_file_id": telegram_file_id},
                model_class=StorageFileSchema,
            )
        except Exception:
            return

    def build_photo_candidates(self, photo_ref: str) -> list[str]:
        raw = str(photo_ref or "").strip()
        if not raw:
            return []
        candidates: list[str] = []
        storage_path = extract_storage_path(raw)
        if storage_path:
            storage_base = os.getenv("STORAGE_SERVICE_HTTP_URL", "").strip().rstrip("/")
            if storage_base:
                candidates.append(f"{storage_base}/storage/{storage_path}")
            public_base = normalize_public_api_base(os.getenv("PUBLIC_API_BASE_URL", "") or os.getenv("NEXT_PUBLIC_API_URL", ""))
            if public_base:
                candidates.append(f"{public_base}/storage/{storage_path}")
                candidates.append(f"{public_base}/api/v1/storage/{storage_path}")
        public_url = to_public_storage_url(raw)
        if public_url:
            candidates.append(public_url)
        candidates.append(raw)
        unique_candidates: list[str] = []
        for candidate in candidates:
            if candidate and candidate.startswith(("http://", "https://")) and candidate not in unique_candidates:
                unique_candidates.append(candidate)
        return unique_candidates

    async def download_photo_bytes(self, photo_ref: str) -> tuple[str, bytes]:
        candidates = self.build_photo_candidates(photo_ref)
        if not candidates:
            raise RuntimeError(f"No photo URL candidates: {photo_ref}")
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for candidate in candidates:
                try:
                    response = await client.get(candidate)
                    response.raise_for_status()
                    content_type = str(response.headers.get("content-type") or "").lower()
                    if content_type and "image/" not in content_type:
                        raise RuntimeError(f"Unsupported content-type for image: {content_type}")
                    filename = Path(candidate.split("?", 1)[0]).name or "image.jpg"
                    return filename, response.content
                except Exception as exc:
                    last_error = exc
        raise RuntimeError(f"Failed to download image: {photo_ref}. Last error: {last_error}")

    async def prepare_image_ref(self, photo_ref: str) -> dict[str, str | None]:
        storage_path = extract_storage_path(photo_ref)
        telegram_file_id = await self.get_storage_file_telegram_file_id(storage_path)
        return {
            "url": str(photo_ref or "").strip(),
            "storage_path": storage_path,
            "telegram_file_id": telegram_file_id,
        }

    def as_input_file(self, filename: str, content: bytes) -> InputFile:
        return InputFile(io.BytesIO(content), filename=filename)
