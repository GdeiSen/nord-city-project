from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.models.service_ticket import ServiceTicket
from shared.models.service_ticket_log import ServiceTicketLog
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
        result = await self.bot.managers.database.service_ticket.create(model_instance=service_ticket, model_class=ServiceTicket)
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

    async def update_service_ticket(self, service_ticket_id: int, update_data: Dict[str, Any]) -> Optional[ServiceTicket]:
        result = await self.bot.managers.database.service_ticket.update(entity_id=service_ticket_id, update_data=update_data, model_class=ServiceTicket)
        if result["success"]:
            return result["data"]
        return None

    async def update_service_ticket_status(self, service_ticket_id: int, status: str, msid: int, user_id: int) -> Optional[ServiceTicketLog]:
        try:
            ticket_status = status
            if status == ServiceTicketStatus.ASSIGNED:
                ticket_status = ServiceTicketStatus.IN_PROGRESS
            result = await self.bot.managers.database.service_ticket.update(
                entity_id=service_ticket_id, update_data={"status": ticket_status}, model_class=ServiceTicket
            )
            if not result.get("success"):
                return None

            log_obj = ServiceTicketLog(
                ticket_id=service_ticket_id,
                status=status,
                msid=msid,
                user_id=user_id
            )
            log_created = await self.bot.services.service_ticket_log.create_service_ticket_log(log_obj)
            return log_created
        except Exception:
            return None

    async def delete_service_ticket(self, service_ticket_id: int) -> bool:
        result = await self.bot.managers.database.service_ticket.delete(entity_id=service_ticket_id)
        if result["success"]:
            return result["data"]
        return False