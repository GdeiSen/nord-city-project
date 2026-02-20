"""
Представление маршрута (экрана) в навигационном стеке.
Аналогия с Flutter Route.
"""
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class Route:
    """
    Простой маршрут — целочисленный идентификатор (Dialogs.*).
    Используется для статических экранов: MENU, SERVICE, PROFILE и т.д.
    """
    route_id: int

    def to_storage(self) -> int:
        """Сериализация для хранения в context."""
        return self.route_id


@dataclass(frozen=True)
class DDIDRoute:
    """
    Маршрут динамического диалога (Dialog-Dialog-Item-ID).
    Формат: "8:1:0:10:1000" = route_id:dialog_id:sequence_id:item_id[:option_id]
    """
    route_id: int  # Dialogs.DYN_DIALOG_ITEM = 8
    dialog_id: int
    sequence_id: int
    item_id: int
    option_id: int | None = None

    def to_storage(self) -> str:
        """Сериализация в формат "8:1:0:10:1000" для хранения."""
        parts = [str(self.route_id), str(self.dialog_id), str(self.sequence_id), str(self.item_id)]
        if self.option_id is not None:
            parts.append(str(self.option_id))
        return ":".join(parts)

    @classmethod
    def from_storage(cls, s: str) -> "DDIDRoute":
        """Парсинг из строки "8:1:0:10:1000"."""
        parts = s.split(":")
        if len(parts) < 4:
            raise ValueError(f"Invalid DDID format: {s}")
        return cls(
            route_id=int(parts[0]),
            dialog_id=int(parts[1]),
            sequence_id=int(parts[2]),
            item_id=int(parts[3]),
            option_id=int(parts[4]) if len(parts) > 4 else None,
        )

    @staticmethod
    def is_ddid(value: str) -> bool:
        """Проверка, является ли строка DDID (содержит двоеточия и числа)."""
        if not isinstance(value, str) or ":" not in value:
            return False
        parts = value.split(":")
        return len(parts) >= 4 and all(p.lstrip("-").isdigit() for p in parts[:4])

    @staticmethod
    def is_back_callback(value: str, route_id: int = 8) -> bool:
        """Проверка формата кнопки 'Назад': '8:-1:dialog_id:seq_id:item_id'."""
        if not isinstance(value, str) or ":" not in value:
            return False
        parts = value.split(":")
        return len(parts) >= 2 and parts[0] == str(route_id) and parts[1] == "-1"

    @classmethod
    def parse_trace_position(cls, s: str) -> tuple[int, int] | None:
        """
        Извлечь (sequence_id, item_id) из DDID-строки для восстановления позиции.
        Возвращает None, если строка не валидный DDID (в т.ч. формат «Назад»).
        """
        if not isinstance(s, str) or ":" not in s:
            return None
        if cls.is_back_callback(s):
            return None
        try:
            ddid = cls.from_storage(s)
            return ddid.sequence_id, ddid.item_id
        except (ValueError, IndexError):
            return None


# Тип элемента стека при хранении (совместимость с текущим trace)
TraceItem = Union[int, str]
