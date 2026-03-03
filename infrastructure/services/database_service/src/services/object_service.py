import logging
from typing import List

from database.database_manager import DatabaseManager
from models.object import Object
from shared.utils.storage_utils import (
    get_removed_storage_paths,
)
from shared.constants import StorageFileCategory
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class ObjectService(BaseService):
    """
    Service for business center object-related logic.
    Inherits all standard CRUD operations from BaseService.
    Cleans up orphaned storage files when photos are updated or entity is deleted.
    """
    model_class = Object

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def _sync_object_files(self, *, session, entity_id: int, urls: list[str]) -> None:
        storage_svc = self.db_manager.services.get("storage_file")
        if storage_svc is None:
            return
        await storage_svc._bind_files(
            session=session,
            entity_type="Object",
            entity_id=int(entity_id),
            urls=urls or [],
            category=StorageFileCategory.DEFAULT,
            meta={"source": "object_photos"},
        )

    @db_session_manager
    async def create(self, *, session, model_instance, **kwargs):
        created = await super().create(session=session, model_instance=model_instance, **kwargs)
        if created is not None:
            await self._sync_object_files(
                session=session,
                entity_id=int(created.id),
                urls=list(created.photos or []),
            )
        return created

    @db_session_manager
    async def get_by_ids(self, *, session, ids: List[int]) -> list:
        """Batch-fetch objects by IDs. Returns list of Object (order not guaranteed)."""
        if not ids:
            return []
        return await self.repository.get_by_ids(session=session, ids=ids)

    @db_session_manager
    async def update(self, *, session, entity_id, update_data, **kwargs):
        """Override to cleanup storage files that are no longer referenced."""
        if "photos" in update_data:
            new_photos = update_data.get("photos")
            new_list = list(new_photos) if new_photos else []
            existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
            storage_svc = self.db_manager.services.get("storage_file")
            if existing:
                old_photos = list(existing.photos) if existing.photos else []
                if storage_svc is not None:
                    for path in get_removed_storage_paths(old_photos, new_list):
                        try:
                            await storage_svc.delete_file(
                                session=session,
                                storage_path=path,
                                remove_reference=False,
                                expected_entity_type="Object",
                                expected_entity_id=int(entity_id),
                            )
                            logger.info("Cleaned up orphaned storage file: %s", path)
                        except Exception as e:
                            logger.warning("Failed to cleanup storage file %s: %s", path, e)
            await self._sync_object_files(
                session=session,
                entity_id=int(entity_id),
                urls=new_list,
            )
        return await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)

    @db_session_manager
    async def delete(self, *, session, entity_id, **kwargs):
        """Override to cleanup storage files when object is deleted."""
        existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
        storage_svc = self.db_manager.services.get("storage_file")
        if existing and existing.photos:
            for url in existing.photos:
                if storage_svc is not None:
                    try:
                        await storage_svc.delete_file(
                            session=session,
                            storage_path=str(url or ""),
                            remove_reference=False,
                            expected_entity_type="Object",
                            expected_entity_id=int(entity_id),
                        )
                        logger.info("Cleaned up storage file on delete: %s", url)
                    except Exception as e:
                        logger.warning("Failed to cleanup storage file %s: %s", url, e)
        await self._sync_object_files(session=session, entity_id=int(entity_id), urls=[])
        return await super().delete(session=session, entity_id=entity_id, **kwargs)
