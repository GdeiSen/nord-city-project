from typing import Any, Optional

from database.database_manager import DatabaseManager
from models.guest_parking_settings import GuestParkingSettings
from shared.constants import StorageFileCategory
from shared.utils.storage_utils import get_removed_storage_paths
from .base_service import BaseService, db_session_manager


class GuestParkingSettingsService(BaseService):
    """Singleton settings for guest parking route images."""

    model_class = GuestParkingSettings
    SETTINGS_ID = 1

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    async def _sync_route_images(
        self,
        *,
        session,
        route_images: list[str],
        audit_context: dict | None = None,
    ) -> None:
        storage_svc = self.db_manager.services.get("storage_file")
        if storage_svc is None:
            return
        await storage_svc._bind_files(
            session=session,
            entity_type="GuestParkingSettings",
            entity_id=self.SETTINGS_ID,
            urls=route_images or [],
            category=StorageFileCategory.SYSTEM,
            meta={"source": "guest_parking_route_images"},
            audit_context=audit_context,
        )

    @db_session_manager
    async def get_settings(self, *, session) -> GuestParkingSettings:
        existing = await self.repository.get_by_id(session=session, entity_id=self.SETTINGS_ID)
        if existing is not None:
            return existing
        return GuestParkingSettings(id=self.SETTINGS_ID, route_images=[])

    @db_session_manager
    async def save_settings(
        self,
        *,
        session,
        route_images: list[str] | None = None,
        **kwargs,
    ) -> GuestParkingSettings:
        audit_context = self._get_audit_context(kwargs)
        normalized_images = [str(url).strip() for url in (route_images or []) if str(url).strip()]
        existing = await self.repository.get_by_id(session=session, entity_id=self.SETTINGS_ID)
        storage_svc = self.db_manager.services.get("storage_file")

        if existing is None:
            created = GuestParkingSettings(id=self.SETTINGS_ID, route_images=normalized_images)
            created = await self.repository.create(session=session, obj_in=created)
            await self._sync_route_images(
                session=session,
                route_images=normalized_images,
                audit_context=audit_context,
            )
            await self._write_audit(
                session,
                self.SETTINGS_ID,
                "create",
                old_data=None,
                new_data={"id": self.SETTINGS_ID, "route_images": normalized_images},
                audit_context=audit_context,
            )
            return created

        old_data = {"id": existing.id, "route_images": list(existing.route_images or [])}
        for path in get_removed_storage_paths(old_data["route_images"], normalized_images):
            if storage_svc is not None:
                await storage_svc.delete_file(
                    session=session,
                    storage_path=path,
                    remove_reference=False,
                    expected_entity_type="GuestParkingSettings",
                    expected_entity_id=self.SETTINGS_ID,
                    _audit_context=audit_context,
                )
        existing.route_images = normalized_images
        updated = await self.repository.update(session=session, obj_in=existing)
        await self._sync_route_images(
            session=session,
            route_images=normalized_images,
            audit_context=audit_context,
        )
        await self._write_audit(
            session,
            self.SETTINGS_ID,
            "update",
            old_data=old_data,
            new_data={"id": self.SETTINGS_ID, "route_images": normalized_images},
            audit_context=audit_context,
        )
        return updated
