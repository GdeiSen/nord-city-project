from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.models.object import Object

if TYPE_CHECKING:
    from bot import Bot

class RentalObjectService(BaseService):
    """Service for managing rental objects."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_object(self, object: Object) -> Optional[Object]:
        result = await self.bot.managers.database.object.create(model_instance=object, model_class=Object)
        if result["success"]:
            return result["data"]
        return None

    async def get_object_by_id(self, object_id: int) -> Optional[Object]:
        result = await self.bot.managers.database.object.get_by_id(entity_id=object_id, model_class=Object)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_objects(self) -> List[Object]:
        result = await self.bot.managers.database.object.get_all(model_class=Object)
        if result["success"]:
            return result["data"]
        return []

    async def update_object(self, object_id: int, update_data: Dict[str, Any]) -> Optional[Object]:
        result = await self.bot.managers.database.object.update(entity_id=object_id, update_data=update_data, model_class=Object)
        if result["success"]:
            return result["data"]
        return None

    async def delete_object(self, object_id: int) -> bool:
        result = await self.bot.managers.database.object.delete(entity_id=object_id)
        if result["success"]:
            return result["data"]
        return False