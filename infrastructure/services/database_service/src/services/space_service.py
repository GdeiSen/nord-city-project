from database.database_manager import DatabaseManager
from shared.models.space import Space
from .base_service import BaseService
from typing import List
from .base_service import db_session_manager

class SpaceService(BaseService):
    """
    Service for space (rental area)-related business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = Space

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_object_id(self, *, session, entity_id: int) -> List[Space]:
        return await self.repository.find(session=session, object_id=entity_id)