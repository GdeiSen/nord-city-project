from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from models.permission import Permission
from models.role import Role, RolePermission
from shared.permissions import EVERYONE_ROLE_CODE, PermissionCodes, SUPER_ADMIN_ROLE_CODE
from shared.utils.converter import Converter

from .base_service import BaseService, db_session_manager


class RoleService(BaseService):
    model_class = Role

    def _serialize_role(self, role: Role) -> dict:
        data = Converter.to_dict(role)
        permissions = [
            rp.permission
            for rp in (getattr(role, "role_permissions", None) or [])
            if getattr(rp, "permission", None) is not None
        ]
        data["permissions"] = Converter.to_dict(permissions)
        data["permission_ids"] = [item.id for item in permissions if getattr(item, "id", None) is not None]
        return data

    @db_session_manager
    async def get_all(self, *, session) -> list[dict]:
        stmt = (
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.is_system.desc(), Role.name.asc(), Role.id.asc())
        )
        result = await session.execute(stmt)
        return [self._serialize_role(role) for role in result.scalars().all()]

    @db_session_manager
    async def get_by_id(self, *, session, entity_id: Any) -> dict | None:
        stmt = (
            select(Role)
            .where(Role.id == int(entity_id))
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        )
        result = await session.execute(stmt)
        role = result.scalars().first()
        return self._serialize_role(role) if role else None

    @db_session_manager
    async def get_by_code(self, *, session, code: str) -> dict | None:
        stmt = (
            select(Role)
            .where(Role.code == str(code).strip())
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        )
        result = await session.execute(stmt)
        role = result.scalars().first()
        return self._serialize_role(role) if role else None

    @db_session_manager
    async def create(self, *, session, model_instance: Role, permission_ids: list[int] | None = None, **kwargs) -> dict:
        role = await super().create(session=session, model_instance=model_instance, **kwargs)
        if permission_ids:
            await self.set_permissions(session=session, role_id=role.id, permission_ids=permission_ids)
        return await self.get_by_id(session=session, entity_id=role.id)

    @db_session_manager
    async def update(self, *, session, entity_id: Any, update_data: dict, **kwargs) -> dict | None:
        permission_ids = update_data.pop("permission_ids", None)
        role = await self.repository.get_by_id(session=session, entity_id=entity_id)
        if role and role.code == SUPER_ADMIN_ROLE_CODE and "code" in update_data:
            update_data.pop("code", None)
        updated = await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)
        if updated is None:
            return None
        if permission_ids is not None:
            await self.set_permissions(session=session, role_id=int(entity_id), permission_ids=permission_ids)
        return await self.get_by_id(session=session, entity_id=entity_id)

    @db_session_manager
    async def set_permissions(self, *, session, role_id: int, permission_ids: list[int]) -> dict | None:
        role = await self.repository.get_by_id(session=session, entity_id=role_id)
        if role is None:
            return None
        normalized_ids = sorted({int(item) for item in (permission_ids or [])})
        if role.code == EVERYONE_ROLE_CODE:
            profile_permission = await session.execute(
                select(Permission.id).where(Permission.code == PermissionCodes.BOT_FEATURE_PROFILE)
            )
            profile_permission_id = profile_permission.scalar_one_or_none()
            if profile_permission_id is not None:
                normalized_ids = sorted(set(normalized_ids) | {int(profile_permission_id)})
        if normalized_ids:
            existing_permissions = await session.execute(
                select(Permission.id).where(Permission.id.in_(normalized_ids))
            )
            valid_ids = {int(item) for item in existing_permissions.scalars().all()}
        else:
            valid_ids = set()
        await session.execute(delete(RolePermission).where(RolePermission.role_id == int(role_id)))
        for permission_id in sorted(valid_ids):
            session.add(RolePermission(role_id=int(role_id), permission_id=permission_id))
        await session.flush()
        return await self.get_by_id(session=session, entity_id=role_id)
