"""
NavigatorManager — навигация по экранам бота (аналог Flutter Navigator).
Использует NavigationStack и Route/DDIDRoute для хранения состояния.
"""
import logging
from typing import Callable, Coroutine, Any, TYPE_CHECKING

from shared.constants import Dialogs, Variables
from shared.entities.navigation_stack import NavigationStack

from .base_manager import BaseManager

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


class NavigatorManager(BaseManager):
    """
    Менеджер навигации с API в стиле Flutter Navigator.
    """

    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.handlers: dict[int | str, Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]] = {}

    async def initialize(self) -> None:
        """Инициализация менеджера навигации."""
        logging.info("NavigatorManager initialized")

    def _get_stack(self, context: "ContextTypes.DEFAULT_TYPE") -> NavigationStack:
        """Получить стек из context."""
        raw = self.bot.managers.storage.get(context, Variables.ACTIVE_DIALOG_TRACE)
        return NavigationStack.from_list(raw or [])

    def _set_stack(self, context: "ContextTypes.DEFAULT_TYPE", stack: NavigationStack) -> None:
        """Сохранить стек в context."""
        self.bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_TRACE, stack.to_list())
        logging.debug("Stack: %s", stack.to_list())

    # --- Регистрация и выполнение ---

    def add_handler(self, key: int, handler: Callable[["Update", "ContextTypes.DEFAULT_TYPE", "Bot"], Coroutine[Any, Any, int | str]]) -> None:
        """Регистрация handler для маршрута."""
        self.handlers[key] = handler

    async def execute(self, key: int | str, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Выполнить переход на экран (push + run handler)."""
        try:
            route_key = int(key) if isinstance(key, str) and key.isdigit() else key
            return await self.push(route_key, update, context)
        except Exception as e:
            logging.exception("Navigation error: %s", e)
            return await self.push(Dialogs.MENU, update, context)

    # --- Flutter-like API ---

    async def push(self, route_id: int | str, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """
        Перейти на экран (Navigator.push).
        Добавляет маршрут в стек и выполняет handler.
        """
        stack = self._get_stack(context)
        route_key = int(route_id) if isinstance(route_id, str) and str(route_id).isdigit() else route_id
        stack.push(route_key)
        self._set_stack(context, stack)
        return await self._execute_handler(route_key, update, context)

    async def pop(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """
        Вернуться на предыдущий экран (Navigator.pop).
        Удаляет текущий маршрут и выполняет handler предыдущего.
        """
        stack = self._get_stack(context)
        if stack.depth < 2:
            await self.push(Dialogs.MENU, update, context)
            return None
        stack.pop()
        self._set_stack(context, stack)
        prev = stack.peek()
        if prev is not None:
            route_key = self._parse_route_key(prev)
            return await self._execute_handler(route_key, update, context)
        return None

    def pop_item(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Удалить последний элемент стека и вернуть его (без выполнения handler)."""
        stack = self._get_stack(context)
        popped = stack.pop()
        self._set_stack(context, stack)
        return popped

    def peek(self, context: "ContextTypes.DEFAULT_TYPE") -> int | str | None:
        """Текущий (верхний) элемент стека."""
        return self._get_stack(context).peek()

    def set_entry_point(self, context: "ContextTypes.DEFAULT_TYPE", route_id: int) -> None:
        """Установить точку входа в ветку навигации."""
        stack = self._get_stack(context)
        stack.clear_and_set_entry(route_id)
        self._set_stack(context, stack)
        logging.debug("Entry point: %s", route_id)

    async def execute_entry_point(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Выполнить экран точки входа (возврат в начало ветки)."""
        stack = self._get_stack(context)
        entry = stack.get_entry_point()
        if entry is not None:
            route_key = self._parse_route_key(entry)
            return await self._execute_handler(route_key, update, context)
        return await self.push(Dialogs.MENU, update, context)

    def get_stack(self, context: "ContextTypes.DEFAULT_TYPE") -> list:
        """Получить текущий стек маршрутов."""
        return self._get_stack(context).to_list()

    def replace_current(self, context: "ContextTypes.DEFAULT_TYPE", item: int | str) -> None:
        """Заменить текущий элемент стека (для DDID при переходе внутри dyn_dialog)."""
        stack = self._get_stack(context)
        stack.replace_current(item)
        self._set_stack(context, stack)
        logging.debug("Replace current: %s", stack.to_list())

    def clear(self, context: "ContextTypes.DEFAULT_TYPE") -> None:
        """Очистить стек навигации."""
        stack = self._get_stack(context)
        stack.clear()
        self._set_stack(context, stack)

    def _parse_route_key(self, item: int | str) -> int | str:
        """Извлечь route_key для вызова handler (int или первый компонент DDID)."""
        if isinstance(item, str) and ":" in item:
            try:
                return int(item.split(":")[0])
            except (ValueError, IndexError):
                return item
        if isinstance(item, str) and item.lstrip("-").isdigit():
            return int(item)
        return item

    async def _execute_handler(self, key: int | str, update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> int | str:
        """Запуск handler по ключу."""
        route_key = self._parse_route_key(key) if isinstance(key, str) else key
        if isinstance(route_key, int) and route_key in self.handlers:
            return await self.handlers[route_key](update, context, self.bot)
        if isinstance(key, str) and ":" in key:
            first = self._parse_route_key(key)
            if isinstance(first, int) and first in self.handlers:
                return await self.handlers[first](update, context, self.bot)
        logging.warning("Unknown route: %s", key)
        return await self.push(Dialogs.MENU, update, context)
