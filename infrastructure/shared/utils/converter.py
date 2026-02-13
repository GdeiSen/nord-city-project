import logging
from typing import Dict, Any, Type, List
from datetime import datetime
from sqlalchemy.inspection import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase, InstanceState
from pydantic import BaseModel

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
            return data.isoformat()
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
        """
        Converts a single value to a JSON-serializable format.
        """
        if isinstance(value, datetime):
            # Преобразуем datetime в строку формата ISO 8601
            return value.isoformat()
        
        # Другие типы (int, str, bool, list, dict, None) уже готовы к сериализации
        return value

    @classmethod
    def from_dict(cls, model_class: type, data: dict) -> Any:
        if not data:
            return model_class()
        # --- Pydantic support ---
        try:
            from pydantic import BaseModel
            if issubclass(model_class, BaseModel):
                if hasattr(model_class, 'model_validate'):
                    return model_class.model_validate(data)
                if hasattr(model_class, 'parse_obj'):
                    return model_class.parse_obj(data)
        except Exception:
            pass
        # --- ORM support ---
        try:
            model_columns = {c.name for c in sa_inspect(model_class).columns}
            filtered_data = {key: value for key, value in data.items() if key in model_columns}
            return model_class(**filtered_data)
        except Exception:
            pass
        # --- Fallback: try to init as plain class ---
        try:
            return model_class(**data)
        except Exception:
            return data