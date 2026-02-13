from database.database_manager import DatabaseManager
from shared.models.feedback import Feedback
from .base_service import BaseService

class FeedbackService(BaseService):
    """
    Service for feedback-related business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = Feedback

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)