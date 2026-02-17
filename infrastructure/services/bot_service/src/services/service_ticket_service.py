from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.models.service_ticket import ServiceTicket
from shared.constants import ServiceTicketStatus
if TYPE_CHECKING:
    from bot import Bot

class ServiceTicketService(BaseService):
    """Service for managing service tickets."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_service_ticket(self, service_ticket: ServiceTicket) -> Optional[ServiceTicket]:
        result = await self.bot.managers.database.service_ticket.create(
            model_instance=service_ticket,
            model_class=ServiceTicket,
            _audit_context={"source": "bot_service"},
        )
        if result["success"]:
            created_ticket = result["data"]
            await self.bot.managers.event.emit('service_ticket_created', created_ticket)
            return created_ticket
        return None

    async def get_service_ticket_by_id(self, service_ticket_id: int) -> Optional[ServiceTicket]:
        result = await self.bot.managers.database.service_ticket.get_by_id(entity_id=service_ticket_id, model_class=ServiceTicket)
        if result["success"]:
            return result["data"]
        return None

    async def get_service_ticket_by_msid(self, msid: int) -> Optional[ServiceTicket]:
        result = await self.bot.managers.database.service_ticket.get_by_msid(msid=msid, model_class=ServiceTicket)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_service_tickets(self) -> List[ServiceTicket]:
        result = await self.bot.managers.database.service_ticket.get_all(model_class=ServiceTicket)
        if result["success"]:
            return result["data"]
        return []

    async def update_service_ticket(
        self,
        service_ticket_id: int,
        update_data: Dict[str, Any],
        _audit_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ServiceTicket]:
        ctx = dict(_audit_context or {})
        ctx.setdefault("source", "bot_service")
        result = await self.bot.managers.database.service_ticket.update(
            entity_id=service_ticket_id,
            update_data=update_data,
            model_class=ServiceTicket,
            _audit_context=ctx,
        )
        if result["success"]:
            return result["data"]
        return None

    async def update_service_ticket_status(
        self,
        service_ticket_id: int,
        status: str,
        msid: int,
        user_id: int,
        assignee: Optional[str] = None,
    ) -> Optional[ServiceTicket]:
        """Update ticket status with meta (msid, assignee). BaseService writes audit.
        ASSIGNED: status stays ASSIGNED, meta records who it was assigned to.
        IN_PROGRESS: set when 'принято'."""
        try:
            meta: Dict[str, Any] = {"msid": msid, "user_id": user_id}
            if assignee:
                meta["assignee"] = assignee
            result = await self.bot.managers.database.service_ticket.update(
                entity_id=service_ticket_id,
                update_data={"status": status},
                model_class=ServiceTicket,
                _audit_context={
                    "source": "bot_service",
                    "assignee_id": user_id,
                    "meta": meta,
                },
            )
            return result.get("data") if result.get("success") else None
        except Exception:
            return None

    async def delete_service_ticket(self, service_ticket_id: int) -> bool:
        result = await self.bot.managers.database.service_ticket.delete(
            entity_id=service_ticket_id,
            _audit_context={"source": "bot_service"},
        )
        if result["success"]:
            return result["data"]
        return False