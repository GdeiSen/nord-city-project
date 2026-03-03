import logging
from typing import List

from database.database_manager import DatabaseManager
from models.space import Space
from shared.utils.storage_utils import (
    get_removed_storage_paths,
)
from shared.constants import StorageFileCategory
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class SpaceService(BaseService):
    """
    Service for space (rental area)-related business logic.
    Inherits all standard CRUD operations from BaseService.
    Cleans up orphaned storage files when photos are updated or entity is deleted.
    """
    model_class = Space

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def _sync_space_files(
        self,
        *,
        session,
        entity_id: int,
        object_id: int | None,
        urls: list[str],
    ) -> None:
        storage_svc = self.db_manager.services.get("storage_file")
        if storage_svc is None:
            return
        await storage_svc._bind_files(
            session=session,
            entity_type="Space",
            entity_id=int(entity_id),
            urls=urls or [],
            category=StorageFileCategory.DEFAULT,
            meta={
                "source": "space_photos",
                "object_id": int(object_id) if object_id is not None else None,
            },
        )

    @db_session_manager
    async def create(self, *, session, model_instance, **kwargs):
        created = await super().create(session=session, model_instance=model_instance, **kwargs)
        if created is not None:
            await self._sync_space_files(
                session=session,
                entity_id=int(created.id),
                object_id=int(created.object_id) if getattr(created, "object_id", None) is not None else None,
                urls=list(created.photos or []),
            )
        return created

    @db_session_manager
    async def get_by_object_id(self, *, session, entity_id: int, only_free: bool = False) -> List[Space]:
        filters = {"object_id": entity_id}
        if only_free:
            filters["status"] = "FREE"
        return await self.repository.find(session=session, **filters)

    @db_session_manager
    async def update(self, *, session, entity_id, update_data, **kwargs):
        """Override to cleanup storage files that are no longer referenced."""
        if "photos" in update_data or "object_id" in update_data:
            existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
            new_list = list(existing.photos) if existing and existing.photos else []
            storage_svc = self.db_manager.services.get("storage_file")
            next_object_id = None
            if existing and getattr(existing, "object_id", None) is not None:
                next_object_id = int(existing.object_id)
            if update_data.get("object_id") is not None:
                next_object_id = int(update_data["object_id"])

            if existing and "photos" in update_data:
                old_photos = list(existing.photos) if existing.photos else []
                new_photos = update_data.get("photos")
                new_list = list(new_photos) if new_photos else []
                if storage_svc is not None:
                    for path in get_removed_storage_paths(old_photos, new_list):
                        try:
                            await storage_svc.delete_file(
                                session=session,
                                storage_path=path,
                                remove_reference=False,
                                expected_entity_type="Space",
                                expected_entity_id=int(entity_id),
                            )
                            logger.info("Cleaned up orphaned storage file: %s", path)
                        except Exception as e:
                            logger.warning("Failed to cleanup storage file %s: %s", path, e)
            await self._sync_space_files(
                session=session,
                entity_id=int(entity_id),
                object_id=next_object_id,
                urls=new_list,
            )
        return await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)

    @db_session_manager
    async def delete(self, *, session, entity_id, **kwargs):
        """Override to cleanup storage files when space is deleted."""
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
                            expected_entity_type="Space",
                            expected_entity_id=int(entity_id),
                        )
                        logger.info("Cleaned up storage file on delete: %s", url)
                    except Exception as e:
                        logger.warning("Failed to cleanup storage file %s: %s", url, e)
        await self._sync_space_files(
            session=session,
            entity_id=int(entity_id),
            object_id=int(existing.object_id) if existing and getattr(existing, "object_id", None) is not None else None,
            urls=[],
        )
        return await super().delete(session=session, entity_id=entity_id, **kwargs)
