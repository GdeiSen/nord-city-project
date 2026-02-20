"""
Стек навигации — хранение цепочки экранов (Route).
Аналогия с Flutter Navigator stack.
"""
from typing import Union

from .route import Route, DDIDRoute, TraceItem


class NavigationStack:
    """
    Стек маршрутов для навигации по экранам бота.
    Поддерживает сериализацию в формат trace (list[int|str]) для хранения в context.
    """

    def __init__(self, items: list[TraceItem] | None = None):
        self._items: list[TraceItem] = list(items or [])

    def push(self, item: TraceItem) -> None:
        """Добавить маршрут в стек (Navigator.push)."""
        # Защита от зацикливания: если item уже есть, обрезать до него
        if item in self._items:
            idx = self._items.index(item)
            self._items = self._items[:idx]
        self._items.append(item)

    def pop(self) -> TraceItem | None:
        """Удалить и вернуть последний элемент (Navigator.pop)."""
        if not self._items:
            return None
        return self._items.pop()

    def peek(self) -> TraceItem | None:
        """Текущий (верхний) элемент без удаления."""
        return self._items[-1] if self._items else None

    def peek_previous(self) -> TraceItem | None:
        """Предыдущий элемент."""
        return self._items[-2] if len(self._items) > 1 else None

    def replace_current(self, item: TraceItem) -> None:
        """Заменить текущий элемент (edit_current_trace_item)."""
        if self._items:
            self._items[-1] = item

    def clear_and_set_entry(self, item: TraceItem) -> None:
        """Очистить стек и установить единственную точку входа."""
        self._items = [item]

    def remove_range(self, start: int, end: int) -> None:
        """Удалить элементы с start по end."""
        self._items = self._items[start:end]

    def clear(self) -> None:
        """Очистить стек."""
        self._items = []

    @property
    def depth(self) -> int:
        """Глубина стека."""
        return len(self._items)

    def to_list(self) -> list[TraceItem]:
        """Список для хранения в context (ACTIVE_DIALOG_TRACE)."""
        return list(self._items)

    @classmethod
    def from_list(cls, items: list[TraceItem] | None) -> "NavigationStack":
        """Восстановление из context."""
        return cls(items or [])

    def get_entry_point(self) -> TraceItem | None:
        """Первый элемент — точка входа в текущую ветку."""
        return self._items[0] if self._items else None
