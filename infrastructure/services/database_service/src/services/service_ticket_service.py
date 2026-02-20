from sqlalchemy import select, func
from database.database_manager import DatabaseManager
from models.service_ticket import ServiceTicket
from .base_service import BaseService, db_session_manager
from shared.schemas.service_tickets_stats import ServiceTicketsStatsSchema
from shared.constants import ServiceTicketStatus

IN_PROGRESS_STATUSES = (
    ServiceTicketStatus.IN_PROGRESS,
    ServiceTicketStatus.ACCEPTED,
    ServiceTicketStatus.ASSIGNED,
)


class ServiceTicketService(BaseService):
    """
    Service for service ticket business logic.
    Inherits standard CRUD operations and can be extended with custom methods.
    """
    model_class = ServiceTicket

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

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
        """Aggregate stats via single SQL query (no full table load)."""
        stmt = select(
            func.count().label("total"),
            func.count().filter(ServiceTicket.status == ServiceTicketStatus.NEW).label("new_count"),
            func.count().filter(ServiceTicket.status.in_(IN_PROGRESS_STATUSES)).label("in_progress_count"),
            func.count().filter(ServiceTicket.status == ServiceTicketStatus.COMPLETED).label("completed_count"),
            func.array_agg(ServiceTicket.id).filter(ServiceTicket.status == ServiceTicketStatus.NEW).label("new_ids"),
            func.array_agg(ServiceTicket.id).filter(ServiceTicket.status.in_(IN_PROGRESS_STATUSES)).label("in_progress_ids"),
            func.array_agg(ServiceTicket.id).filter(ServiceTicket.status == ServiceTicketStatus.COMPLETED).label("completed_ids"),
        ).select_from(ServiceTicket)
        result = await session.execute(stmt)
        row = result.one()
        return ServiceTicketsStatsSchema(
            total_count=row.total or 0,
            new_count=row.new_count or 0,
            in_progress_count=row.in_progress_count or 0,
            completed_count=row.completed_count or 0,
            new_tickets=list(row.new_ids or []),
            in_progress_tickets=list(row.in_progress_ids or []),
            completed_tickets=list(row.completed_ids or []),
        )