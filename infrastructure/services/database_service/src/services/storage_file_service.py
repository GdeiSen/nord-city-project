import json
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from sqlalchemy import select

from database.database_manager import DatabaseManager
from models.guest_parking_settings import GuestParkingSettings
from models.object import Object
from models.service_ticket import ServiceTicket
from models.space import Space
from models.storage_file import StorageFile
from shared.clients.storage_client import storage_client
from shared.constants import StorageFileCategory, StorageFileKind
from shared.utils.converter import Converter
from shared.utils.storage_utils import STORAGE_PATH_PATTERN, extract_storage_path

from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class StorageFileService(BaseService):
    """Registry service for all uploaded files stored by the storage layer."""

    model_class = StorageFile

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @staticmethod
    def _normalize_path(value: str) -> str | None:
        candidate = str(value or "").strip()
        if not candidate:
            return None

        path = extract_storage_path(candidate)
        if path:
            return path

        fallback = candidate.lstrip("/")
        if fallback.startswith("storage/"):
            fallback = fallback[8:].lstrip("/")

        return fallback if fallback and STORAGE_PATH_PATTERN.match(fallback) else None

    @staticmethod
    def _infer_kind(original_name: str, content_type: str | None = None) -> str:
        content = str(content_type or "").lower()
        extension = Path(str(original_name or "")).suffix.lower()

        if content.startswith("image/") or extension in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
            return StorageFileKind.IMAGE
        if content.startswith("video/") or extension in {".mp4", ".webm", ".mov"}:
            return StorageFileKind.VIDEO
        if (
            content.startswith("text/")
            or content in {
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
            or extension in {".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".csv"}
        ):
            return StorageFileKind.DOCUMENT
        return StorageFileKind.OTHER

    @staticmethod
    def _normalize_meta(meta: Optional[dict]) -> dict | None:
        if not meta:
            return None
        try:
            return dict(meta)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _merge_meta(cls, current_meta: Optional[dict], meta_updates: Optional[dict]) -> dict | None:
        current = cls._normalize_meta(current_meta) or {}
        updates = cls._normalize_meta(meta_updates)
        if updates is None:
            return current or None
        current.update(updates)
        return current or None

    @classmethod
    def _remove_url_from_list(cls, urls: list | None, target_path: str) -> list[str]:
        cleaned: list[str] = []
        for item in urls or []:
            candidate = str(item or "").strip()
            if not candidate:
                continue
            if cls._normalize_path(candidate) == target_path:
                continue
            if candidate not in cleaned:
                cleaned.append(candidate)
        return cleaned

    async def _detach_bound_reference(self, *, session, item: StorageFile) -> None:
        entity_type = str(item.entity_type or "").strip()
        entity_id = item.entity_id
        if not entity_type or entity_id is None:
            return

        if entity_type == "Object":
            entity = await session.get(Object, int(entity_id))
            if entity is None:
                return
            entity.photos = self._remove_url_from_list(list(entity.photos or []), item.storage_path)
            await self.db_manager.repositories.get(Object).update(session=session, obj_in=entity)
            return

        if entity_type == "Space":
            entity = await session.get(Space, int(entity_id))
            if entity is None:
                return
            entity.photos = self._remove_url_from_list(list(entity.photos or []), item.storage_path)
            await self.db_manager.repositories.get(Space).update(session=session, obj_in=entity)
            return

        if entity_type == "GuestParkingSettings":
            entity = await session.get(GuestParkingSettings, int(entity_id))
            if entity is None:
                return
            entity.route_images = self._remove_url_from_list(list(entity.route_images or []), item.storage_path)
            await self.db_manager.repositories.get(GuestParkingSettings).update(session=session, obj_in=entity)
            return

        if entity_type == "ServiceTicket":
            entity = await session.get(ServiceTicket, int(entity_id))
            if entity is None:
                return

            next_image = str(entity.image or "").strip() or None
            if next_image and self._normalize_path(next_image) == item.storage_path:
                next_image = None

            meta_dict: dict = {}
            if isinstance(entity.meta, dict):
                meta_dict = dict(entity.meta)
            elif isinstance(entity.meta, str) and entity.meta.strip():
                try:
                    parsed = json.loads(entity.meta)
                    if isinstance(parsed, dict):
                        meta_dict = parsed
                except (TypeError, ValueError):
                    meta_dict = {}

            attachments = meta_dict.get("attachments") if isinstance(meta_dict, dict) else []
            next_attachments = self._remove_url_from_list(
                list(attachments) if isinstance(attachments, list) else [],
                item.storage_path,
            )
            if next_attachments:
                meta_dict["attachments"] = next_attachments
            else:
                meta_dict.pop("attachments", None)

            entity.image = next_image
            entity.meta = json.dumps(meta_dict, ensure_ascii=False) if meta_dict else None
            await self.db_manager.repositories.get(ServiceTicket).update(session=session, obj_in=entity)
            return

        raise ValueError(
            f"Cannot safely detach storage file bound to unsupported entity "
            f"{entity_type}#{entity_id}"
        )

    async def _register_upload(
        self,
        *,
        session,
        storage_path: str,
        public_url: str,
        original_name: str,
        content_type: str | None,
        size_bytes: int,
        extension: str | None,
        kind: str,
        category: str,
        meta: Optional[dict] = None,
    ) -> StorageFile:
        existing = await session.scalar(
            select(StorageFile).where(StorageFile.storage_path == storage_path)
        )
        encoded_meta = self._normalize_meta(meta)

        if existing:
            existing.public_url = public_url
            existing.original_name = original_name
            existing.content_type = content_type
            existing.size_bytes = int(size_bytes or 0)
            existing.extension = extension
            existing.kind = kind
            existing.category = category
            if encoded_meta is not None:
                existing.meta = self._merge_meta(existing.meta, encoded_meta)
            updated = await self.repository.update(session=session, obj_in=existing)
            return updated

        model = StorageFile(
            storage_path=storage_path,
            public_url=public_url,
            original_name=original_name,
            content_type=content_type,
            extension=extension,
            size_bytes=int(size_bytes or 0),
            kind=kind or self._infer_kind(original_name, content_type),
            category=category or StorageFileCategory.DEFAULT,
            meta=encoded_meta,
        )
        created = await self.repository.create(session=session, obj_in=model)
        return created

    async def _bind_files(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        urls: list[str],
        category: str = StorageFileCategory.DEFAULT,
        meta: Optional[dict] = None,
    ) -> list[StorageFile]:
        url_map: dict[str, str] = {}
        for url in urls or []:
            path = self._normalize_path(url)
            if path and path not in url_map:
                url_map[path] = str(url or "").strip()

        desired_paths = list(url_map.keys())

        existing_bound = (
            await session.execute(
                select(StorageFile).where(
                    StorageFile.entity_type == entity_type,
                    StorageFile.entity_id == int(entity_id),
                    StorageFile.category == category,
                )
            )
        ).scalars().all()

        for item in existing_bound:
            if item.storage_path not in desired_paths:
                item.entity_type = None
                item.entity_id = None
                await self.repository.update(session=session, obj_in=item)

        if not desired_paths:
            return []

        existing_items = (
            await session.execute(
                select(StorageFile).where(StorageFile.storage_path.in_(desired_paths))
            )
        ).scalars().all()
        item_map = {item.storage_path: item for item in existing_items}
        bound_items: list[StorageFile] = []

        for path in desired_paths:
            item = item_map.get(path)
            if item is None:
                original_name = path.split("_", 1)[1] if "_" in path else path
                guessed_content_type = mimetypes.guess_type(original_name)[0]
                item = StorageFile(
                    storage_path=path,
                    public_url=url_map[path],
                    original_name=original_name,
                    content_type=guessed_content_type,
                    extension=Path(original_name).suffix.lower() or None,
                    size_bytes=0,
                    kind=self._infer_kind(original_name, guessed_content_type),
                    category=category,
                    meta=self._merge_meta(None, meta),
                )
                item = await self.repository.create(session=session, obj_in=item)
                item_map[path] = item

            item.public_url = url_map[path]
            item.entity_type = entity_type
            item.entity_id = int(entity_id)
            item.category = category
            if meta:
                item.meta = self._merge_meta(item.meta, meta)
            updated = await self.repository.update(session=session, obj_in=item)
            bound_items.append(updated)

        return bound_items

    @db_session_manager
    async def register_upload(
        self,
        *,
        session,
        storage_path: str,
        public_url: str,
        original_name: str,
        content_type: str | None = None,
        size_bytes: int = 0,
        extension: str | None = None,
        kind: str | None = None,
        category: str = StorageFileCategory.DEFAULT,
        meta: Optional[dict] = None,
    ) -> Optional[StorageFile]:
        path = self._normalize_path(storage_path)
        if not path:
            return None
        ext = extension or (Path(original_name).suffix.lower() or None)
        detected_kind = kind or self._infer_kind(original_name, content_type)
        return await self._register_upload(
            session=session,
            storage_path=path,
            public_url=public_url,
            original_name=original_name,
            content_type=content_type,
            size_bytes=size_bytes,
            extension=ext,
            kind=detected_kind,
            category=category,
            meta=meta,
        )

    @db_session_manager
    async def bind_files(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        urls: list[str],
        category: str = StorageFileCategory.DEFAULT,
        meta: Optional[dict] = None,
    ) -> list[StorageFile]:
        if not entity_type or entity_id is None:
            return []
        return await self._bind_files(
            session=session,
            entity_type=entity_type,
            entity_id=entity_id,
            urls=urls or [],
            category=category,
            meta=meta,
        )

    @db_session_manager
    async def find_by_entity(
        self,
        *,
        session,
        entity_type: str,
        entity_id: int,
        model_class=None,
    ) -> list[StorageFile]:
        if not entity_type or entity_id is None:
            return []
        rows = await session.execute(
            select(StorageFile)
            .where(
                StorageFile.entity_type == entity_type,
                StorageFile.entity_id == int(entity_id),
            )
            .order_by(StorageFile.created_at.asc(), StorageFile.id.asc())
        )
        return list(rows.scalars().all())

    @db_session_manager
    async def find_by_path(
        self,
        *,
        session,
        storage_path: str,
        model_class=None,
    ) -> Optional[StorageFile]:
        path = self._normalize_path(storage_path)
        if not path:
            return None
        return await session.scalar(
            select(StorageFile).where(StorageFile.storage_path == path)
        )

    @db_session_manager
    async def merge_meta_by_path(
        self,
        *,
        session,
        storage_path: str,
        meta_updates: Optional[dict] = None,
        model_class=None,
    ) -> Optional[StorageFile]:
        path = self._normalize_path(storage_path)
        if not path:
            return None

        item = await session.scalar(
            select(StorageFile).where(StorageFile.storage_path == path)
        )
        if item is None:
            return None

        normalized_current = self._normalize_meta(item.meta)
        merged_meta = self._merge_meta(item.meta, meta_updates)
        if merged_meta == normalized_current:
            return item

        item.meta = merged_meta
        return await self.repository.update(session=session, obj_in=item)

    @db_session_manager
    async def delete_file(
        self,
        *,
        session,
        storage_path: str,
        remove_reference: bool = True,
        expected_entity_type: str | None = None,
        expected_entity_id: int | None = None,
        **kwargs,
    ) -> bool:
        audit_context = self._get_audit_context(kwargs)
        path = self._normalize_path(storage_path)
        if not path:
            return False

        item = await session.scalar(
            select(StorageFile).where(StorageFile.storage_path == path)
        )

        if item is None:
            try:
                await storage_client.connect()
                await storage_client.delete(path)
            except Exception as exc:
                logger.warning("Failed to cleanup missing registry file %s: %s", path, exc)
            return False

        is_expected_binding = (
            bool(expected_entity_type)
            and item.entity_type == expected_entity_type
            and expected_entity_id is not None
            and item.entity_id == int(expected_entity_id)
        )

        if item.entity_type and item.entity_id is not None:
            if remove_reference:
                await self._detach_bound_reference(session=session, item=item)
            elif not is_expected_binding:
                raise ValueError(
                    f"Storage file {path} is still bound to "
                    f"{item.entity_type}#{item.entity_id}"
                )

        old_data = Converter.to_dict(item)

        await storage_client.connect()
        try:
            await storage_client.delete(path)
        except Exception as exc:
            if "not found" not in str(exc).lower():
                raise
            logger.info("Storage object %s was already absent during delete.", path)

        deleted = await self.repository.delete(session=session, entity_id=int(item.id))
        if deleted and old_data is not None:
            await self._write_audit(
                session,
                int(item.id),
                "delete",
                old_data=old_data,
                new_data=None,
                audit_context=audit_context,
            )
        return bool(deleted)
