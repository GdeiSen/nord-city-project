from database.database_manager import DatabaseManager
from models.user_auth import UserAuth
from .base_service import BaseService

class AuthService(BaseService):
    """
    Service for authentication-related business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = UserAuth

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)