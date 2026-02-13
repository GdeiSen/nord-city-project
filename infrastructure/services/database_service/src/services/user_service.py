from database.database_manager import DatabaseManager
from shared.models.user import User
from .base_service import BaseService

class UserService(BaseService):
    """Service for user-related business logic."""
    model_class = User

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)