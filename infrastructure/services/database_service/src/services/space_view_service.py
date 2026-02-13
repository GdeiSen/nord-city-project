from database.database_manager import DatabaseManager
from shared.models.space_view import SpaceView
from .base_service import BaseService

class SpaceViewService(BaseService):
    """
    Service for SpaceView related business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = SpaceView

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)