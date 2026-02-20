from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.schemas import ObjectSchema

if TYPE_CHECKING:
    from bot import Bot

class RentalObjectService(BaseService):
    """Service for managing rental objects."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_object(self, object: ObjectSchema) -> Optional[ObjectSchema]:
        result = await self.bot.managers.database.object.create(model_instance=object, model_class=ObjectSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_object_by_id(self, object_id: int) -> Optional[ObjectSchema]:
        result = await self.bot.managers.database.object.get_by_id(entity_id=object_id, model_class=ObjectSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_objects(self) -> List[ObjectSchema]:
        result = await self.bot.managers.database.object.get_all(model_class=ObjectSchema)
        if result["success"]:
            return result["data"]
        return []

    async def get_available_objects(self) -> List[ObjectSchema]:
        """Returns only objects with status='ACTIVE' (visible on site, shown in bot)."""
        all_objs = await self.get_all_objects()
        result = []
        for obj in all_objs:
            if (obj.status or "ACTIVE") == "ACTIVE":
                result.append(obj)
        return result

    async def update_object(self, object_id: int, update_data: Dict[str, Any]) -> Optional[ObjectSchema]:
        result = await self.bot.managers.database.object.update(entity_id=object_id, update_data=update_data, model_class=ObjectSchema)
        if result["success"]:
            return result["data"]
        return None

    async def delete_object(self, object_id: int) -> bool:
        result = await self.bot.managers.database.object.delete(entity_id=object_id)
        if result["success"]:
            return result["data"]
        return False