from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.schemas import UserAccessSchema, UserSchema

if TYPE_CHECKING:
    from bot import Bot


class UserService(BaseService):
    """Service for managing users."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_user(
        self,
        user: UserSchema,
        *,
        _audit_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserSchema]:
        result = await self.bot.managers.database.user.create(
            model_instance=user,
            model_class=UserSchema,
            _audit_context=_audit_context,
        )
        if result["success"]:
            return result["data"]
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[UserSchema]:
        result = await self.bot.managers.database.user.get_by_id(entity_id=user_id, model_class=UserSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_users(self) -> List[UserSchema]:
        result = await self.bot.managers.database.user.get_all(model_class=UserSchema)
        if result["success"]:
            return result["data"] or []
        return []

    async def get_access_profile(self, user_id: int) -> UserAccessSchema | None:
        result = await self.bot.managers.database.user.get_access_profile(
            user_id=user_id,
            model_class=UserAccessSchema,
        )
        if result.get("success"):
            return result.get("data")
        return None

    async def has_permission(self, user_id: int, permission_code: str) -> bool:
        access = await self.get_access_profile(user_id)
        return bool(access and (access.is_super_admin or permission_code in set(access.permissions or [])))

    async def update_user(
        self,
        user_id: int,
        update_data: Dict[str, Any],
        *,
        _audit_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserSchema]:
        result = await self.bot.managers.database.user.update(
            entity_id=user_id,
            update_data=update_data,
            model_class=UserSchema,
            _audit_context=_audit_context,
        )
        if result["success"]:
            return result["data"]
        return None

    async def delete_user(
        self,
        user_id: int,
        *,
        _audit_context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        result = await self.bot.managers.database.user.delete(
            entity_id=user_id,
            _audit_context=_audit_context,
        )
        if result["success"]:
            return result["data"]
        return False
