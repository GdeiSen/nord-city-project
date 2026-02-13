from database.database_manager import DatabaseManager
from shared.models.object import Object
from .base_service import BaseService

class ObjectService(BaseService):
    """
    Service for business center object-related logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = Object

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)