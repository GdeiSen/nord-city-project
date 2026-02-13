from database.database_manager import DatabaseManager
from shared.models.service_ticket import ServiceTicket
from .base_service import BaseService, db_session_manager
# You can import other models if this service needs to interact with them
# from shared.models.service_ticket_log import ServiceTicketLog
from shared.entities.service_tickets_stats import ServiceTicketsStats
from shared.constants import ServiceTicketStatus

class ServiceTicketService(BaseService):
    """
    Service for service ticket business logic.
    Inherits standard CRUD operations and can be extended with custom methods.
    """
    model_class = ServiceTicket

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)
        # If this service needs to work with other repositories, get them here.
        # For example, to manage logs related to tickets:
        # from shared.models.service_ticket_log import ServiceTicketLog
        # self.log_repository = self.db_manager.repositories.get(ServiceTicketLog)

    # You can add custom business logic methods here.
    # For example:
    # @db_session_manager
    # async def get_statistics(self, *, session):
    #     # ... custom logic to calculate statistics ...
    #     pass

    @db_session_manager
    async def get_by_msid(self, *, session, msid: int) -> ServiceTicket | None:
        results = await self.repository.find(session=session, msid=msid)
        return results[0] if results else None

    @db_session_manager
    async def get_stats(self, *, session):
        tickets = await self.repository.get_all(session=session)
        new_tickets = [t for t in tickets if getattr(t, 'status', None) == ServiceTicketStatus.NEW]
        in_progress_tickets = [t for t in tickets if getattr(t, 'status', None) in (ServiceTicketStatus.IN_PROGRESS, ServiceTicketStatus.ACCEPTED, ServiceTicketStatus.ASSIGNED)]
        completed_tickets = [t for t in tickets if getattr(t, 'status', None) == ServiceTicketStatus.COMPLETED]
        stats = ServiceTicketsStats(
            total_count=len(tickets),
            new_count=len(new_tickets),
            in_progress_count=len(in_progress_tickets),
            completed_count=len(completed_tickets),
            new_tickets=[t.id for t in new_tickets],
            in_progress_tickets=[t.id for t in in_progress_tickets],
            completed_tickets=[t.id for t in completed_tickets],
        )
        return stats.model_dump()