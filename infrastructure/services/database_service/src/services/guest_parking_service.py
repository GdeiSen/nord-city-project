"""
Сервис заявок на гостевую парковку.

Логика напоминаний: in-memory кэш в database_service, без поля reminder_sent_at в БД.
- Кэш предстоящих заявок (по arrival_date).
- find_due_for_reminder читает из кэша, не из БД.
- При create: добавляем в кэш, если не полон.
- При update/delete: удаляем из кэша.
- Каждую минуту: 1) отдаём due заявки и удаляем их из кэша, 2) очистка просроченных (arrival прошёл).
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select

from database.database_manager import DatabaseManager
from models.guest_parking_request import GuestParkingRequest
from shared.utils.time_utils import now, to_system_time
from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)

# Макс. размер кэша напоминаний (самые ранние заявки)
REMINDER_CACHE_MAX_SIZE = 500

# Окно напоминания: за 13–16 минут до arrival (при проверке раз в минуту)
REMINDER_WINDOW_START_MIN = 13
REMINDER_WINDOW_END_MIN = 16


def _to_cache_item(record: Any) -> dict:
    """Преобразует ORM/dict в элемент кэша."""
    if isinstance(record, dict):
        return {
            "id": record.get("id"),
            "arrival_date": record.get("arrival_date"),
            "license_plate": record.get("license_plate", ""),
            "car_make_color": record.get("car_make_color", ""),
            "driver_phone": record.get("driver_phone", ""),
        }
    return {
        "id": getattr(record, "id", None),
        "arrival_date": getattr(record, "arrival_date", None),
        "license_plate": getattr(record, "license_plate", "") or "",
        "car_make_color": getattr(record, "car_make_color", "") or "",
        "driver_phone": getattr(record, "driver_phone", "") or "",
    }


class GuestParkingService(BaseService):
    """Сервис для заявок на гостевую парковку с in-memory кэшем напоминаний."""

    model_class = GuestParkingRequest

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)
        self._reminder_cache: list[dict] = []
        self._reminder_cache_lock = asyncio.Lock()
        self._last_notification_minute: Optional[str] = None  # "YYYY-MM-DD HH:MM" — флаг: оповестили в эту минуту

    async def init_reminder_cache(self) -> None:
        """Загружает предстоящие заявки в кэш при старте. Сортировка по arrival_date ascending."""
        async with self._reminder_cache_lock:
            try:
                async with self.db_manager.get_session() as session:
                    now_dt = now()
                    # Будущие заявки на ближайшие 7 дней
                    horizon = now_dt + timedelta(days=7)
                    stmt = (
                        select(GuestParkingRequest)
                        .where(GuestParkingRequest.arrival_date >= now_dt)
                        .where(GuestParkingRequest.arrival_date <= horizon)
                        .order_by(GuestParkingRequest.arrival_date.asc())
                        .limit(REMINDER_CACHE_MAX_SIZE)
                    )
                    result = await session.execute(stmt)
                    rows = list(result.scalars().all())
                self._reminder_cache = [_to_cache_item(r) for r in rows]
                logger.info("Guest parking reminder cache loaded: %d items", len(self._reminder_cache))
            except Exception as e:
                logger.error("Failed to load reminder cache: %s", e)
                self._reminder_cache = []

    async def _add_to_cache_if_not_full(self, item: dict) -> None:
        """Добавляет заявку в кэш, если не полон. arrival_date должен быть в будущем."""
        arr = item.get("arrival_date")
        if arr is None:
            return
        if isinstance(arr, str):
            try:
                arr = datetime.fromisoformat(arr.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                return
        if arr.tzinfo:
            arr = to_system_time(arr)
        if arr <= now():
            return
        cache_item = _to_cache_item(item)
        async with self._reminder_cache_lock:
            if len(self._reminder_cache) >= REMINDER_CACHE_MAX_SIZE:
                return
            self._reminder_cache.append(cache_item)
            self._reminder_cache.sort(key=lambda x: x.get("arrival_date") or datetime.max)

    def _remove_from_cache_by_id_sync(self, entity_id: int) -> None:
        """Удаляет заявку из кэша по id. Вызывать только внутри lock."""
        self._reminder_cache = [c for c in self._reminder_cache if c.get("id") != entity_id]

    def _cleanup_expired(self, now_dt: datetime) -> None:
        """Удаляет из кэша заявки, у которых arrival_date уже прошёл."""
        def _is_future(c: dict) -> bool:
            a = c.get("arrival_date")
            if a is None:
                return False
            if isinstance(a, datetime):
                adt = to_system_time(a) if a.tzinfo else a
            else:
                try:
                    adt = datetime.fromisoformat(str(a).replace("Z", "+00:00"))
                    if adt.tzinfo:
                        adt = to_system_time(adt)
                except (ValueError, TypeError):
                    return False
            return adt > now_dt

        self._reminder_cache = [c for c in self._reminder_cache if _is_future(c)]

    async def find_due_for_reminder(self, *, reference_time_iso: str | None = None, **kwargs) -> list:
        """
        Возвращает заявки из кэша, по которым нужно напоминание (окно 13–16 мин до arrival).
        После отдачи удаляет их из кэша. Очистка просроченных — после «цикла оповещения».
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

        minute_key = now_dt.strftime("%Y-%m-%d %H:%M")

        async with self._reminder_cache_lock:
            # 1. Если новая минута — сначала очистка просроченных (предыдущий цикл оповещения завершён)
            if self._last_notification_minute is not None and minute_key != self._last_notification_minute:
                self._cleanup_expired(now_dt)
                self._last_notification_minute = None

            window_start = now_dt + timedelta(minutes=REMINDER_WINDOW_START_MIN)
            window_end = now_dt + timedelta(minutes=REMINDER_WINDOW_END_MIN)

            def _arr_dt(c: dict):
                a = c.get("arrival_date")
                if a is None:
                    return None
                if isinstance(a, datetime):
                    return to_system_time(a) if a.tzinfo else a
                try:
                    return datetime.fromisoformat(str(a).replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    return None

            due_items = []
            rest = []
            for c in self._reminder_cache:
                adt = _arr_dt(c)
                if adt is None:
                    rest.append(c)
                    continue
                if window_start <= adt <= window_end:
                    due_items.append(c)
                else:
                    rest.append(c)

            self._reminder_cache = rest
            self._last_notification_minute = minute_key
            return due_items

    @db_session_manager
    async def create(self, *, session, model_instance: Any, **kwargs) -> Optional[Any]:
        """Создаёт заявку и добавляет в кэш напоминаний, если не полон."""
        created = await super().create(session=session, model_instance=model_instance, **kwargs)
        if created:
            await self._add_to_cache_if_not_full(_to_cache_item(created))
        return created

    @db_session_manager
    async def update(self, *, session, entity_id: Any, update_data: dict, **kwargs) -> Optional[Any]:
        """Обновляет заявку и пересинхронизирует кэш (удаляем, при необходимости добавим при следующей загрузке)."""
        result = await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)
        if result:
            async with self._reminder_cache_lock:
                self._remove_from_cache_by_id_sync(int(entity_id))
            await self._add_to_cache_if_not_full(_to_cache_item(result))
        return result

    @db_session_manager
    async def delete(self, *, session, entity_id: Any, **kwargs) -> bool:
        """Удаляет заявку и убирает из кэша."""
        result = await super().delete(session=session, entity_id=entity_id, **kwargs)
        if result:
            async with self._reminder_cache_lock:
                self._remove_from_cache_by_id_sync(int(entity_id))
        return result
