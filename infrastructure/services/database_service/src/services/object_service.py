import logging
from typing import Any, List

from database.database_manager import DatabaseManager
from models.object import Object
from models.user import User
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

    async def _validate_feedback_recipient_user(
        self,
        *,
        session,
        user_id: Any,
    ) -> None:
        if user_id is None:
            return
        user_repo = self.db_manager.repositories.get(User)
        user = await user_repo.get_by_id(session=session, entity_id=int(user_id))
        if user is None:
            raise ValueError(f"Feedback recipient user {user_id} not found")

    async def _sync_object_files_with_audit(
        self,
        *,
        session,
        entity_id: int,
        urls: list[str],
        audit_context: dict | None,
    ) -> None:
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
            audit_context=audit_context,
        )

    @db_session_manager
    async def create(self, *, session, model_instance, **kwargs):
        audit_context = self._get_audit_context(kwargs)
        recipient_user_id = (
            model_instance.get("service_feedback_recipient_user_id")
            if isinstance(model_instance, dict)
            else getattr(model_instance, "service_feedback_recipient_user_id", None)
        )
        await self._validate_feedback_recipient_user(
            session=session,
            user_id=recipient_user_id,
        )
        created = await super().create(
            session=session,
            model_instance=model_instance,
            _audit_context=audit_context,
            **kwargs,
        )
        if created is not None:
            await self._sync_object_files_with_audit(
                session=session,
                entity_id=int(created.id),
                urls=list(created.photos or []),
                audit_context=audit_context,
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
        audit_context = self._get_audit_context(kwargs)
        if "service_feedback_recipient_user_id" in update_data:
            await self._validate_feedback_recipient_user(
                session=session,
                user_id=update_data.get("service_feedback_recipient_user_id"),
            )
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
                                _audit_context=audit_context,
                            )
                            logger.info("Cleaned up orphaned storage file: %s", path)
                        except Exception as e:
                            logger.warning("Failed to cleanup storage file %s: %s", path, e)
            await self._sync_object_files_with_audit(
                session=session,
                entity_id=int(entity_id),
                urls=new_list,
                audit_context=audit_context,
            )
        return await super().update(
            session=session,
            entity_id=entity_id,
            update_data=update_data,
            _audit_context=audit_context,
            **kwargs,
        )

    @db_session_manager
    async def delete(self, *, session, entity_id, **kwargs):
        """Override to cleanup storage files when object is deleted."""
        audit_context = self._get_audit_context(kwargs)
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
                            _audit_context=audit_context,
                        )
                        logger.info("Cleaned up storage file on delete: %s", url)
                    except Exception as e:
                        logger.warning("Failed to cleanup storage file %s: %s", url, e)
        await self._sync_object_files_with_audit(
            session=session,
            entity_id=int(entity_id),
            urls=[],
            audit_context=audit_context,
        )
        return await super().delete(
            session=session,
            entity_id=entity_id,
            _audit_context=audit_context,
            **kwargs,
        )
