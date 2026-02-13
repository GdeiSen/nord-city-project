import logging
from typing import Callable, Coroutine, Any, TYPE_CHECKING
from shared.constants import Dialogs, Variables
from .base_manager import BaseManager

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


class RouterManager(BaseManager):
    """Менеджер для управления маршрутизацией диалогов"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.dialogs: dict[int, Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]] = {}
        self.handlers: dict[int, Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]] = {}
        self.map_to_parent: dict[int, int | str] = {}

    async def initialize(self) -> None:
        """Инициализация менеджера маршрутизации"""
        print("RouterManager initialized")

    async def execute_previous(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Выполнение предыдущего элемента в трассировке"""
        current_trace = self.get_current_trace(context)
        if not current_trace or len(current_trace) < 2:
            print("execute_previous: current_trace is empty or too short")
            await self.execute(Dialogs.MENU, update, context)
        self.pop_previous_trace_item(context)
        previous_item = self.get_current_trace_item(context)
        if previous_item is None:
            print("execute_previous: previous_item is None")
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
                    print(f"Invalid key: {key}")
            if key in self.dialogs:
                return await self.dialogs[key](update, context, self.bot)
            elif key in self.handlers:
                return await self.handlers[key](update, context, self.bot)
            else:
                print(f"Unknown key: {key}")
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
        logging.info(f"set_current_trace: {current_trace}")

    def add_trace_item(self, context: "ContextTypes.DEFAULT_TYPE", item: int | str):
        """Добавление элемента в трассировку"""
        current_trace = self.get_current_trace(context)
        
        # Проверяем, существует ли уже элемент с таким ключом в трассировке
        if item in current_trace:
            # Находим индекс первого вхождения этого элемента
            index = current_trace.index(item)
            # Обрезаем трассировку до этого индекса
            current_trace = current_trace[:index]
            logging.info(f"add_trace_item: обнаружено зацикливание, удаляем элементы после {item}")
        
        # Добавляем элемент в трассировку
        current_trace.append(item)
        self._set_current_trace(context, current_trace)
        logging.info(f"add_trace_item: {current_trace}")

    def set_entry_point_item(self, context: "ContextTypes.DEFAULT_TYPE", item: int):
        """Установка точки входа"""
        self._set_current_trace(context, [item])
        logging.info(f"set_entry_point_item: {item}")

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
        logging.info(f"pop_previous_trace_item: current_trace before pop: {current_trace}")
        if not current_trace:
            logging.info("pop_previous_trace_item: current_trace is empty")
            return None
        prev_trace_item = current_trace.pop()
        logging.info(f"pop_previous_trace_item: removing {prev_trace_item} from {current_trace}")
        self._set_current_trace(context, current_trace)
        logging.info(f"pop_previous_trace_item: current_trace after set: {self.get_current_trace(context)}")
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
            logging.info(f"edit_current_trace_item: {current_trace}")

    async def restore_dialog_state(self, user_id: int, context: "ContextTypes.DEFAULT_TYPE") -> int | None:
        """Восстановление состояния диалога"""
        return None 