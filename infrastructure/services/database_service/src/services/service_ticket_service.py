import json

from sqlalchemy import select, func
from database.database_manager import DatabaseManager
from models.service_ticket import ServiceTicket
from .base_service import BaseService, db_session_manager
from shared.schemas.service_tickets_stats import ServiceTicketsStatsSchema
from shared.constants import ServiceTicketStatus, StorageFileCategory

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

    @staticmethod
    def _extract_attachment_urls(ticket: ServiceTicket) -> list[str]:
        urls: list[str] = []
        if ticket.image:
            urls.append(str(ticket.image).strip())

        meta = ticket.meta
        meta_dict = {}
        if isinstance(meta, str) and meta.strip():
            try:
                meta_dict = json.loads(meta)
            except (TypeError, ValueError):
                meta_dict = {}
        elif isinstance(meta, dict):
            meta_dict = meta

        attachments = meta_dict.get("attachments") if isinstance(meta_dict, dict) else []
        if isinstance(attachments, list):
            for item in attachments:
                candidate = str(item or "").strip()
                if candidate and candidate not in urls:
                    urls.append(candidate)
        return urls

    async def _sync_ticket_files(self, *, session, ticket: ServiceTicket | None) -> None:
        if ticket is None or getattr(ticket, "id", None) is None:
            return
        storage_svc = self.db_manager.services.get("storage_file")
        if storage_svc is None:
            return
        await storage_svc._bind_files(
            session=session,
            entity_type="ServiceTicket",
            entity_id=int(ticket.id),
            urls=self._extract_attachment_urls(ticket),
            category=StorageFileCategory.DEFAULT,
            meta={"source": "service_ticket"},
        )

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
    async def create(self, *, session, model_instance, **kwargs):
        created = await super().create(session=session, model_instance=model_instance, **kwargs)
        await self._sync_ticket_files(session=session, ticket=created)
        return created

    @db_session_manager
    async def update(self, *, session, entity_id, update_data, **kwargs):
        updated = await super().update(
            session=session,
            entity_id=entity_id,
            update_data=update_data,
            **kwargs,
        )
        await self._sync_ticket_files(session=session, ticket=updated)
        return updated

    @db_session_manager
    async def delete(self, *, session, entity_id, **kwargs):
        existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
        storage_svc = self.db_manager.services.get("storage_file")
        if storage_svc is not None and existing is not None:
            await storage_svc._bind_files(
                session=session,
                entity_type="ServiceTicket",
                entity_id=int(entity_id),
                urls=[],
                category=StorageFileCategory.DEFAULT,
            )
        return await super().delete(session=session, entity_id=entity_id, **kwargs)

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
