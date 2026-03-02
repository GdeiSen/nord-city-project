from typing import Any, Optional

from database.database_manager import DatabaseManager
from models.guest_parking_settings import GuestParkingSettings
from .base_service import BaseService, db_session_manager


class GuestParkingSettingsService(BaseService):
    """Singleton settings for guest parking route images."""

    model_class = GuestParkingSettings
    SETTINGS_ID = 1

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

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

        if existing is None:
            created = GuestParkingSettings(id=self.SETTINGS_ID, route_images=normalized_images)
            created = await self.repository.create(session=session, obj_in=created)
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
        existing.route_images = normalized_images
        updated = await self.repository.update(session=session, obj_in=existing)
        await self._write_audit(
            session,
            self.SETTINGS_ID,
            "update",
            old_data=old_data,
            new_data={"id": self.SETTINGS_ID, "route_images": normalized_images},
            audit_context=audit_context,
        )
        return updated
