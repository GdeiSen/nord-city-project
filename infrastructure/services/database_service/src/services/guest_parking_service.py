from datetime import datetime, timedelta

from sqlalchemy import select

from database.database_manager import DatabaseManager
from models.guest_parking_request import GuestParkingRequest
from shared.utils.time_utils import now, to_system_time
from .base_service import BaseService, db_session_manager


class GuestParkingService(BaseService):
    """Сервис для заявок на гостевую парковку."""

    model_class = GuestParkingRequest

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def find_due_for_reminder(self, *, session, reference_time_iso: str | None = None) -> list:
        """
        Находит заявки, по которым нужно отправить напоминание за 15 минут до заезда.
        reference_time_iso: текущее время в ISO (из TimeUtils.now()) для согласованного часового пояса.
        Окно [now+13:00, now+16:00] — даёт запас при ежеминутной проверке.
        """
        if reference_time_iso:
            try:
                now_dt = datetime.fromisoformat(reference_time_iso.replace("Z", "+00:00"))
                if now_dt.tzinfo:
                    now_dt = to_system_time(now_dt)
            except (ValueError, TypeError):
                now_dt = now()
        else:
            now_dt = now()
        window_start = now_dt + timedelta(minutes=13)
        window_end = now_dt + timedelta(minutes=16)
        stmt = (
            select(GuestParkingRequest)
            .where(GuestParkingRequest.arrival_date >= window_start)
            .where(GuestParkingRequest.arrival_date <= window_end)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
