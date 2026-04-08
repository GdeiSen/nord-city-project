from typing import List, Optional

from sqlalchemy import select

from database.database_manager import DatabaseManager
from models.service_ticket_feedback_ref import ServiceTicketFeedbackRef
from .base_service import BaseService, db_session_manager


class ServiceTicketFeedbackRefService(BaseService):
    """Queries and maintains service ticket <-> feedback one-to-one links."""

    model_class = ServiceTicketFeedbackRef

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_service_ticket_id(
        self,
        *,
        session,
        service_ticket_id: int,
    ) -> Optional[ServiceTicketFeedbackRef]:
        stmt = select(ServiceTicketFeedbackRef).where(
            ServiceTicketFeedbackRef.service_ticket_id == int(service_ticket_id)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @db_session_manager
    async def get_by_feedback_id(
        self,
        *,
        session,
        feedback_id: int,
    ) -> Optional[ServiceTicketFeedbackRef]:
        stmt = select(ServiceTicketFeedbackRef).where(
            ServiceTicketFeedbackRef.feedback_id == int(feedback_id)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @db_session_manager
    async def get_by_service_ticket_ids(
        self,
        *,
        session,
        service_ticket_ids: List[int],
    ) -> List[ServiceTicketFeedbackRef]:
        normalized_ids = sorted({int(item) for item in (service_ticket_ids or [])})
        if not normalized_ids:
            return []
        stmt = select(ServiceTicketFeedbackRef).where(
            ServiceTicketFeedbackRef.service_ticket_id.in_(normalized_ids)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @db_session_manager
    async def get_by_feedback_ids(
        self,
        *,
        session,
        feedback_ids: List[int],
    ) -> List[ServiceTicketFeedbackRef]:
        normalized_ids = sorted({int(item) for item in (feedback_ids or [])})
        if not normalized_ids:
            return []
        stmt = select(ServiceTicketFeedbackRef).where(
            ServiceTicketFeedbackRef.feedback_id.in_(normalized_ids)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
