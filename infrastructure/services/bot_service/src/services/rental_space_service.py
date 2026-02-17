from typing import TYPE_CHECKING, Optional, Dict, Any, List
from .base_service import BaseService
from shared.models.space import Space

if TYPE_CHECKING:
    from bot import Bot

class RentalSpaceService(BaseService):
    """Service for managing rental objects."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_space(self, space: Space) -> Optional[Space]:
        result = await self.bot.managers.database.space.create(model_instance=space, model_class=Space)
        if result["success"]:
            return result["data"]
        return None

    async def get_space_by_id(self, space_id: int) -> Optional[Space]:
        result = await self.bot.managers.database.space.get_by_id(entity_id=space_id, model_class=Space)
        if result["success"]:
            return result["data"]
        return None

    async def get_spaces_by_object_id(self, object_id: int, only_free: bool = False) -> List[Space]:
        result = await self.bot.managers.database.space.get_by_object_id(
            entity_id=object_id, only_free=only_free, model_class=Space
        )
        if result["success"]:
            return result["data"]
        return []

    async def get_free_spaces_by_object_id(self, object_id: int) -> List[Space]:
        """Returns only spaces with status='FREE' for the given object."""
        return await self.get_spaces_by_object_id(object_id, only_free=True)

    async def get_all_spaces(self) -> List[Space]:
        result = await self.bot.managers.database.space.get_all(model_class=Space)
        if result["success"]:
            return result["data"]
        return []

    async def update_space(self, space_id: int, update_data: Dict[str, Any]) -> Optional[Space]:
        result = await self.bot.managers.database.space.update(entity_id=space_id, update_data=update_data, model_class=Space)
        if result["success"]:
            return result["data"]
        return None

    async def delete_space(self, space_id: int) -> bool:
        result = await self.bot.managers.database.space.delete(entity_id=space_id)
        if result["success"]:
            return result["data"]
        return False