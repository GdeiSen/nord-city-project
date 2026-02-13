from typing import TYPE_CHECKING, List, Optional, Dict, Any
from .base_service import BaseService
from shared.models.service_ticket_log import ServiceTicketLog
import logging
logger = logging.getLogger(__name__)

class ServiceTicketLogService(BaseService):
    """Service for managing service ticket logs."""

    def __init__(self, bot: "Bot"):
        super().__init__(bot)

    async def initialize(self) -> None:
        pass

    async def create_service_ticket_log(self, service_ticket_log: ServiceTicketLog) -> Optional[ServiceTicketLog]:
        print(f"[PRINT] create_service_ticket_log: input={service_ticket_log}")
        result = await self.bot.managers.database.service_ticket_log.create(
            model_instance=service_ticket_log, model_class=ServiceTicketLog
        )
        print(f"[PRINT] create_service_ticket_log: db_result={result}")
        if result["success"]:
            print(f"[PRINT] create_service_ticket_log: returning data={result['data']}")
            return result["data"]
        else:
            print(f"[PRINT] create_service_ticket_log: error={result.get('error')}")
            return None

    async def get_service_ticket_log_by_id(self, service_ticket_log_id: int) -> Optional[ServiceTicketLog]:
        result = await self.bot.managers.database.service_ticket_log.get_by_id(entity_id=service_ticket_log_id, model_class=ServiceTicketLog)
        if result["success"]:
            return result["data"]
        return None

    async def get_all_service_ticket_logs(self) -> List[ServiceTicketLog]:
        result = await self.bot.managers.database.service_ticket_log.get_all(model_class=ServiceTicketLog)
        if result["success"]:
            return result["data"]
        return []

    async def update_service_ticket_log(self, service_ticket_log_id: int, update_data: Dict[str, Any]) -> Optional[ServiceTicketLog]:
        result = await self.bot.managers.database.service_ticket_log.update(entity_id=service_ticket_log_id, update_data=update_data)
        if result["success"]:
            return result["data"]
        return None

    async def delete_service_ticket_log(self, service_ticket_log_id: int) -> bool:
        result = await self.bot.managers.database.service_ticket_log.delete(entity_id=service_ticket_log_id)
        if result["success"]:
            return result["data"]
        return False