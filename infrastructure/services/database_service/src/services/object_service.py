import logging
from typing import List

from database.database_manager import DatabaseManager
from shared.models.object import Object
from shared.utils.media_urls import get_removed_media_paths, extract_media_path
from shared.clients.media_client import media_client
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class ObjectService(BaseService):
    """
    Service for business center object-related logic.
    Inherits all standard CRUD operations from BaseService.
    Cleans up orphaned media files when photos are updated or entity is deleted.
    """
    model_class = Object

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_ids(self, *, session, ids: List[int]) -> list:
        """Batch-fetch objects by IDs. Returns list of Object (order not guaranteed)."""
        if not ids:
            return []
        return await self.repository.get_by_ids(session=session, ids=ids)

    @db_session_manager
    async def update(self, *, session, entity_id, update_data, **kwargs):
        """Override to cleanup media files that are no longer referenced."""
        if "photos" in update_data:
            existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
            if existing:
                old_photos = list(existing.photos) if existing.photos else []
                new_photos = update_data.get("photos")
                new_list = list(new_photos) if new_photos else []
                for path in get_removed_media_paths(old_photos, new_list):
                    try:
                        await media_client.connect()
                        await media_client.delete(path)
                        logger.info("Cleaned up orphaned media: %s", path)
                    except Exception as e:
                        logger.warning("Failed to cleanup media %s: %s", path, e)
        return await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)

    @db_session_manager
    async def delete(self, *, session, entity_id, **kwargs):
        """Override to cleanup media files when object is deleted."""
        existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
        if existing and existing.photos:
            for url in existing.photos:
                path = extract_media_path(str(url) if url else "")
                if path:
                    try:
                        await media_client.connect()
                        await media_client.delete(path)
                        logger.info("Cleaned up media on delete: %s", path)
                    except Exception as e:
                        logger.warning("Failed to cleanup media %s: %s", path, e)
        return await super().delete(session=session, entity_id=entity_id, **kwargs)