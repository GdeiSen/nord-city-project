import logging
from typing import Callable, Coroutine, Any, TYPE_CHECKING
from shared.constants import Dialogs, Variables
from .base_manager import BaseManager

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


logger = logging.getLogger(__name__)


class RouterManager(BaseManager):
    """Менеджер для управления маршрутизацией диалогов"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.dialogs: dict[int, Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]] = {}
        self.handlers: dict[int, Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]] = {}
        self.map_to_parent: dict[int, int | str] = {}

    async def initialize(self) -> None:
        """Инициализация менеджера маршрутизации"""
        logger.info("RouterManager initialized")

    async def execute_previous(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Выполнение предыдущего элемента в трассировке"""
        current_trace = self.get_current_trace(context)
        if not current_trace or len(current_trace) < 2:
            logger.warning("execute_previous: current_trace is empty or too short")
            await self.execute(Dialogs.MENU, update, context)
        self.pop_previous_trace_item(context)
        previous_item = self.get_current_trace_item(context)
        if previous_item is None:
            logger.warning("execute_previous: previous_item is None")
            await self.execute(Dialogs.MENU, update, context)
        return await self.execute(previous_item, update, context)

    def add_handler(self, key: int, handler: Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int]]):
        """Добавление обработчика"""
        self.handlers[key] = handler

    async def execute(self, key: int | str, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Выполнение действия по ключу"""
        try:
            self.add_trace_item(context, key)
            
            if isinstance(key, str):
                try:
                    key = int(key)
                except ValueError:
                    logger.warning("Invalid navigation key: %s", key)
            if key in self.dialogs:
                return await self.dialogs[key](update, context, self.bot)
            elif key in self.handlers:
                return await self.handlers[key](update, context, self.bot)
            else:
                logger.warning("Unknown navigation key: %s", key)
                await self.execute(Dialogs.MENU, update, context)
        except Exception as e:
            raise e
            await self.execute(Dialogs.MENU, update, context)

    def get_current_trace(self, context: "ContextTypes.DEFAULT_TYPE") -> list[int | str]:
        """Получение текущей трассировки"""
        current_trace = self.bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_TRACE)
        return current_trace or []

    def _set_current_trace(self, context: "ContextTypes.DEFAULT_TYPE", current_trace: list[int | str]):
        """Установка текущей трассировки"""
        self.bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_TRACE, current_trace)
        logger.info("set_current_trace: %s", current_trace)

    def add_trace_item(self, context: "ContextTypes.DEFAULT_TYPE", item: int | str):
        """Добавление элемента в трассировку"""
        current_trace = self.get_current_trace(context)
        
        # Проверяем, существует ли уже элемент с таким ключом в трассировке
        if item in current_trace:
            # Находим индекс первого вхождения этого элемента
            index = current_trace.index(item)
            # Обрезаем трассировку до этого индекса
            current_trace = current_trace[:index]
            logger.info("add_trace_item: detected loop, trimming trace after %s", item)
        
        # Добавляем элемент в трассировку
        current_trace.append(item)
        self._set_current_trace(context, current_trace)
        logger.info("add_trace_item: %s", current_trace)

    def set_entry_point_item(self, context: "ContextTypes.DEFAULT_TYPE", item: int):
        """Установка точки входа"""
        self._set_current_trace(context, [item])
        logger.info("set_entry_point_item: %s", item)

    async def execute_entry_point_item(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        """Выполнение точки входа"""
        current_trace = self.get_current_trace(context)
        if current_trace:
            await self.execute(current_trace[0], update, context)
        else:
            await self.execute(Dialogs.MENU, update, context)

    def remove_trace_items(self, context: "ContextTypes.DEFAULT_TYPE", start: int, end: int):
        """Удаление элементов из трассировки"""
        current_trace = self.get_current_trace(context)
        self._set_current_trace(context, current_trace[start:end])

    def pop_previous_trace_item(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Удаление предыдущего элемента из трассировки"""
        current_trace = self.get_current_trace(context)
        logger.info("pop_previous_trace_item: current_trace before pop: %s", current_trace)
        if not current_trace:
            logger.info("pop_previous_trace_item: current_trace is empty")
            return None
        prev_trace_item = current_trace.pop()
        logger.info("pop_previous_trace_item: removing %s from %s", prev_trace_item, current_trace)
        self._set_current_trace(context, current_trace)
        logger.info("pop_previous_trace_item: current_trace after set: %s", self.get_current_trace(context))
        return prev_trace_item

    def get_entry_point_item(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Получение точки входа"""
        current_trace = self.get_current_trace(context)
        return current_trace[0] if current_trace else None

    def get_current_trace_item(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Получение текущего элемента трассировки"""
        current_trace = self.get_current_trace(context)
        return current_trace[-1] if current_trace else None

    def get_previous_trace_item(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Получение предыдущего элемента трассировки"""
        current_trace = self.get_current_trace(context)
        return current_trace[-2] if len(current_trace) > 1 else None

    def edit_current_trace_item(self, context: "ContextTypes.DEFAULT_TYPE", item: int | str):
        """Редактирование текущего элемента трассировки"""
        current_trace = self.get_current_trace(context)
        if current_trace:
            current_trace[-1] = item
            self._set_current_trace(context, current_trace)
            logger.info("edit_current_trace_item: %s", current_trace)

    async def restore_dialog_state(self, user_id: int, context: "ContextTypes.DEFAULT_TYPE") -> int | None:
        """Восстановление состояния диалога"""
        return None 
