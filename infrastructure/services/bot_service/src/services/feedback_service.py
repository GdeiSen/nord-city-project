from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.schemas import FeedbackSchema
from telegram import Update, Message
from telegram.ext import ContextTypes

if TYPE_CHECKING:
    from bot import Bot

class FeedbackService(BaseService):
    """Service for managing feedback and quality surveys."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_feedback(self, feedback: FeedbackSchema) -> Optional[FeedbackSchema]:
        result = await self.bot.managers.database.feedback.create(model_instance=feedback, model_class=FeedbackSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_feedback_by_id(self, feedback_id: int) -> Optional[FeedbackSchema]:
        result = await self.bot.managers.database.feedback.get_by_id(entity_id=feedback_id, model_class=FeedbackSchema)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_feedbacks(self) -> List[FeedbackSchema]:
        result = await self.bot.managers.database.feedback.get_all(model_class=FeedbackSchema)
        if result["success"]:
            return result["data"]
        return []

    async def update_feedback(self, feedback_id: int, update_data: Dict[str, Any]) -> Optional[FeedbackSchema]:
        result = await self.bot.managers.database.feedback.update(entity_id=feedback_id, update_data=update_data, model_class=FeedbackSchema)
        if result["success"]:
            return result["data"]
        return None

    async def delete_feedback(self, feedback_id: int) -> bool:
        result = await self.bot.managers.database.feedback.delete(entity_id=feedback_id)
        if result["success"]:
            return result["data"]
        return False