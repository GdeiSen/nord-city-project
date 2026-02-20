from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.schemas import PollAnswerSchema

if TYPE_CHECKING:
    from bot import Bot

class PollService(BaseService):
    """Service for managing polls."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_poll(self, poll: PollAnswerSchema) -> Optional[PollAnswerSchema]:
        result = await self.bot.managers.database.poll.create(model_instance=poll, model_class=PollAnswerSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_poll_by_id(self, poll_id: int) -> Optional[PollAnswerSchema]:
        result = await self.bot.managers.database.poll.get_by_id(entity_id=poll_id, model_class=PollAnswerSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_polls(self) -> List[PollAnswerSchema]:
        result = await self.bot.managers.database.poll.get_all(model_class=PollAnswerSchema)
        if result["success"]:
            return result["data"]
        return []

    async def update_poll(self, poll_id: int, update_data: Dict[str, Any]) -> Optional[PollAnswerSchema]:
        result = await self.bot.managers.database.poll.update(entity_id=poll_id, update_data=update_data, model_class=PollAnswerSchema)
        if result["success"]:
            return result["data"]
        return None

    async def delete_poll(self, poll_id: int) -> bool:
        result = await self.bot.managers.database.poll.delete(entity_id=poll_id)
        if result["success"]:
            return result["data"]
        return False

    async def find_poll_answers(self, user_id: int, ddid: str) -> List[PollAnswerSchema]:
        """
        Finds poll answers by user_id and ddid.
        
        Args:
            user_id: The ID of the user who answered
            ddid: Dialog ID in format "0000-0000-0000" (dialog_id-sequence_id-item_id)
            
        Returns:
            List of matching PollAnswerSchema instances
        """
        result = await self.bot.managers.database.poll.find(
            filters={'user_id': user_id, 'ddid': ddid},
            model_class=PollAnswerSchema
        )
        if result["success"]:
            return result["data"] if result["data"] else []
        return []