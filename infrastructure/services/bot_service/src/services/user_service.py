from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.schemas import UserSchema

if TYPE_CHECKING:
    from bot import Bot


class UserService(BaseService):
    """Service for managing users."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_user(self, user: UserSchema) -> Optional[UserSchema]:
        result = await self.bot.managers.database.user.create(model_instance=user, model_class=UserSchema)
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

    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[UserSchema]:
        result = await self.bot.managers.database.user.update(
            entity_id=user_id, update_data=update_data, model_class=UserSchema
        )
        if result["success"]:
            return result["data"]
        return None

    async def delete_user(self, user_id: int) -> bool:
        result = await self.bot.managers.database.user.delete(entity_id=user_id)
        if result["success"]:
            return result["data"]
        return False