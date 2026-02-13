from database.database_manager import DatabaseManager
from shared.models.poll_answer import PollAnswer
from .base_service import BaseService

class PollService(BaseService):
    """
    Service for poll answer-related business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = PollAnswer

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)