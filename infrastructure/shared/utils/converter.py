import logging
from typing import Dict, Any, Type, List
from datetime import datetime, timezone
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase, InstanceState
from pydantic import BaseModel

from shared.utils.time_utils import SYSTEM_TIMEZONE

logger = logging.getLogger(__name__)

class Converter:
    """
    A utility for converting between SQLAlchemy models and dictionaries.
    This is crucial for serializing/deserializing objects for RPC calls.
    """

    @classmethod
    def to_dict(cls, data: Any) -> Any:
        """
        Recursively converts a SQLAlchemy model instance or a list of them
        into a dictionary format suitable for JSON serialization.
        It correctly handles nested models and datetime objects.
        """
        if data is None:
            return None
        if isinstance(data, list):
            return [cls.to_dict(item) for item in data]
        # --- Pydantic support ---
        if isinstance(data, BaseModel):
            return data.model_dump()
        if hasattr(data, '_sa_instance_state') and isinstance(data._sa_instance_state, InstanceState):
            return cls._model_to_dict(data)
        if isinstance(data, dict):
            return {k: cls.to_dict(v) for k, v in data.items()}
        if isinstance(data, datetime):
            s = data.isoformat()
            # Z добавляем только для ORM (ответ из БД) в _serialize_value.
            # Здесь — сериализация dict (model_data, update_data): naive = local, Z не добавляем.
            if data.tzinfo is not None:
                # aware: приводим к UTC для однозначной сериализации
                data = data.astimezone(timezone.utc)
                s = data.isoformat().replace("+00:00", "Z")
            return s
        return data

    @classmethod
    def _model_to_dict(cls, model_instance: DeclarativeBase) -> Dict[str, Any]:
        """
        Converts a single SQLAlchemy model instance to a dictionary,
        serializing special types like datetime to strings.
        """
        if not model_instance:
            return {}
        
        state = sa_inspect(model_instance)
        # --- ИЗМЕНЕНИЕ ЛОГИКИ ЗДЕСЬ ---
        # Теперь мы не просто копируем значение, а пропускаем его через сериализатор
        return {c.key: cls._serialize_value(getattr(model_instance, c.key)) for c in state.mapper.column_attrs}

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Сериализация значения для JSON. TIMESTAMPTZ возвращает aware (UTC)."""
        if isinstance(value, datetime):
            s = value.isoformat()
            if value.tzinfo is None and "+" not in s and "Z" not in s:
                s += "Z"
            return s
        
        # Другие типы (int, str, bool, list, dict, None) уже готовы к сериализации
        return value

    @classmethod
    def from_dict(cls, model_class: type, data: dict | Any) -> Any:
        """
        Преобразует словарь в экземпляр модели. Всегда возвращает модель, никогда словарь.
        При ошибке конвертации выбрасывает исключение.
        """
        if data is None:
            return None
        if not isinstance(data, dict):
            if hasattr(data, "_sa_instance_state"):
                return data  # уже экземпляр ORM
            raise TypeError(f"from_dict ожидает dict, получено: {type(data)}")
        if not data:
            return model_class()

        try:
            # Pydantic
            from pydantic import BaseModel
            if issubclass(model_class, BaseModel):
                return model_class.model_validate(data) if hasattr(model_class, "model_validate") else model_class.parse_obj(data)
        except Exception:
            pass

        # SQLAlchemy ORM
        if hasattr(model_class, "__table__"):
            table = model_class.__table__
            datetime_cols = set()
            from sqlalchemy import DateTime
            for col in table.c:
                if isinstance(col.type, DateTime):
                    datetime_cols.add(col.key)

            col_keys = {c.key for c in table.c}
            filtered = {}
            for key, value in data.items():
                if key not in col_keys:
                    continue
                if key in datetime_cols:
                    if isinstance(value, str):
                        try:
                            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass
                    # TIMESTAMP WITH TIME ZONE: naive → Europe/Minsk
                    if isinstance(value, datetime) and value.tzinfo is None:
                        value = value.replace(tzinfo=SYSTEM_TIMEZONE)
                filtered[key] = value
            return model_class(**filtered)

        # Fallback: dataclass/plain class
        return model_class(**{k: v for k, v in data.items() if hasattr(model_class, k)})

    @classmethod
    def normalize_for_model(cls, model_class: type, data: dict) -> dict:
        """
        Приводит значения dict к типам, ожидаемым ORM (для update_data).
        Строки даты/времени → datetime. Naive → Europe/Minsk для TIMESTAMPTZ.
        """
        if not data or not hasattr(model_class, "__table__"):
            return dict(data)
        from sqlalchemy import DateTime
        table = model_class.__table__
        datetime_cols = {c.key for c in table.c if isinstance(c.type, DateTime)}
        result = dict(data)
        for key in list(result.keys()):
            if key not in datetime_cols:
                continue
            value = result[key]
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
            if isinstance(value, datetime) and value.tzinfo is None:
                value = value.replace(tzinfo=SYSTEM_TIMEZONE)
            result[key] = value
        return result