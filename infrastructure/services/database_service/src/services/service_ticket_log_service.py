from database.database_manager import DatabaseManager
from shared.models.service_ticket_log import ServiceTicketLog
from .base_service import BaseService

class ServiceTicketLogService(BaseService):
    """
    Service for service ticket log business logic.
    Inherits all standard CRUD operations from BaseService.
    """
    model_class = ServiceTicketLog

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)