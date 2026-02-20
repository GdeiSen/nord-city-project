import json
import logging
from functools import wraps
from typing import Type, TypeVar, Any, Optional, List, Dict

from sqlalchemy.orm import DeclarativeBase
from database.database_manager import DatabaseManager
from shared.utils.converter import Converter
from shared.utils.audit_diff import compute_smart_diff

from shared.constants import (
    AUDITED_ENTITY_TYPES,
    AUDIT_ENTITY_MODES,
    AUDIT_MODE_FAST,
    AUDIT_MODE_SMART,
    AUDIT_MODE_HEAVY,
    AUDIT_SKIP_UPDATE_FIELDS,
    AUDIT_HEAVY_MAX_JSON_BYTES,
)

ModelType = TypeVar('ModelType', bound=DeclarativeBase)

logger = logging.getLogger(__name__)

def db_session_manager(func):
    """
    A decorator that manages database sessions for service methods.
    It provides a `session` keyword argument, handles transactions, and logs exceptions.
    """
    @wraps(func)
    async def wrapper(self: 'BaseService', *args, **kwargs):
        if not hasattr(self, 'db_manager') or not isinstance(self.db_manager, DatabaseManager):
            raise TypeError(f"Object {self.__class__.__name__} needs a 'db_manager' to use @db_session_manager.")

        # Ensure session is not passed manually
        kwargs.pop('session', None)

        try:
            async with self.db_manager.get_session() as session:
                return await func(self, *args, session=session, **kwargs)
        except Exception as e:
            logger.error(
                f"Exception in service method '{self.__class__.__name__}.{func.__name__}': {e}",
                exc_info=True
            )
            raise
    return wrapper


class BaseService:
    """
    A generic base service providing standard CRUD operations.
    It works directly with SQLAlchemy model instances. Subclasses must define 'model_class'.
    """
    model_class: Type[ModelType] = None

    def __init__(self, db_manager: DatabaseManager):
        """
        Initializes the service with a DatabaseManager instance.

        Args:
            db_manager: The central manager for database resources.
        """
        if self.model_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} must define a 'model_class' attribute.")
        self.db_manager = db_manager
        self.repository = self.db_manager.repositories.get(self.model_class)

    def _get_audit_context(self, kwargs: dict) -> Optional[dict]:
        """Extract and remove _audit_context from kwargs (assignee_id, source, meta, ...)."""
        return kwargs.pop("_audit_context", None)

    def _limit_audit_json_size(self, data: Optional[dict]) -> Optional[dict]:
        """Limit JSON size for heavy audit; replace with placeholder if exceeded."""
        if data is None:
            return None
        try:
            encoded = json.dumps(data, ensure_ascii=False, default=str)
            if len(encoded.encode("utf-8")) <= AUDIT_HEAVY_MAX_JSON_BYTES:
                return data
            return {"_truncated": True, "_reason": "size_exceeded", "_bytes": len(encoded.encode("utf-8"))}
        except (TypeError, ValueError):
            return {"_truncated": True, "_reason": "serialization_error"}

    def _resolve_audit_data(
        self,
        action: str,
        mode: str,
        old_data: Optional[dict],
        new_data: Optional[dict],
    ) -> tuple[Optional[dict], Optional[dict]]:
        """Resolve old_data/new_data based on audit mode."""
        if mode == AUDIT_MODE_FAST:
            return None, None
        if mode == AUDIT_MODE_HEAVY:
            return self._limit_audit_json_size(old_data), self._limit_audit_json_size(new_data)
        if mode == AUDIT_MODE_SMART:
            if action == "create":
                return None, self._limit_audit_json_size(new_data)
            if action == "delete":
                return self._limit_audit_json_size(old_data), None
            if action == "update" and old_data is not None and new_data is not None:
                diff = compute_smart_diff(old_data, new_data)
                return None, self._limit_audit_json_size(diff) if diff else None
            return self._limit_audit_json_size(old_data), self._limit_audit_json_size(new_data)
        return None, None

    async def _write_audit(
        self,
        session,
        entity_id: int,
        action: str,
        old_data: Optional[dict],
        new_data: Optional[dict],
        audit_context: Optional[dict],
    ) -> None:
        """Write audit log entry if entity is audited."""
        if self.model_class.__name__ not in AUDITED_ENTITY_TYPES:
            return
        audit_svc = self.db_manager.services.get("audit_log")
        if audit_svc is None or not hasattr(audit_svc, "append"):
            return
        mode = AUDIT_ENTITY_MODES.get(self.model_class.__name__, AUDIT_MODE_FAST)
        stored_old, stored_new = self._resolve_audit_data(action, mode, old_data, new_data)
        assignee_id = (audit_context.get("assignee_id") or audit_context.get("user_id")) if audit_context else None
        meta = audit_context.get("meta") if audit_context else {}
        if not isinstance(meta, dict):
            meta = {}
        meta = dict(meta)
        if "source" not in meta and audit_context and audit_context.get("source"):
            meta["source"] = audit_context["source"]
        try:
            await audit_svc.append(
                session=session,
                entity_type=self.model_class.__name__,
                entity_id=entity_id,
                action=action,
                old_data=stored_old,
                new_data=stored_new,
                meta=meta if meta else {},
                assignee_id=assignee_id,
                audit_type=mode,
            )
        except Exception as e:
            logger.warning("Failed to write audit log: %s", e)

    @db_session_manager
    async def create(self, *, session, model_instance: ModelType, **kwargs) -> Optional[ModelType]:
        """
        Creates a new entity in the database from a model instance.
        ID will be automatically generated by PostgreSQL sequences for models with autoincrement.
        """
        audit_context = self._get_audit_context(kwargs)
        # Если model_instance — dict, преобразуем в модель
        if isinstance(model_instance, dict):
            model_instance = Converter.from_dict(self.model_class, model_instance)

        created_instance = await self.repository.create(session=session, obj_in=model_instance)
        if created_instance is None:
            raise Exception(f"Failed to create new {self.model_class.__name__} in the database.")
        logger.info(f"{self.model_class.__name__} created with ID: {getattr(created_instance, 'id', 'N/A')}")

        entity_id = getattr(created_instance, "id", None)
        if entity_id is not None:
            await self._write_audit(
                session, entity_id, "create",
                old_data=None, new_data=Converter.to_dict(created_instance),
                audit_context=audit_context,
            )
        return created_instance

    @db_session_manager
    async def get_by_id(self, *, session, entity_id: Any) -> Optional[ModelType]:
        """Retrieves an entity by its primary key."""
        return await self.repository.get_by_id(session=session, entity_id=entity_id)

    @db_session_manager
    async def get_all(self, *, session) -> List[ModelType]:
        """Retrieves all entities of this type."""
        return await self.repository.get_all(session=session)

    @db_session_manager
    async def get_paginated(
        self,
        *,
        session,
        page: int = 1,
        page_size: int = 10,
        sort: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        search_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Returns paginated {items: [...], total: int}."""
        return await self.repository.get_paginated(
            session=session,
            page=page,
            page_size=page_size,
            sort=sort,
            filters=filters,
            search=search,
            search_columns=search_columns,
        )

    @db_session_manager
    async def update(self, *, session, entity_id: Any, update_data: Dict[str, Any], **kwargs) -> Optional[ModelType]:
        """
        Updates an existing entity from a dictionary of changes.
        """
        audit_context = self._get_audit_context(kwargs)
        existing_model = await self.repository.get_by_id(session=session, entity_id=entity_id)
        if not existing_model:
            return None

        update_data = Converter.normalize_for_model(self.model_class, update_data)
        old_data = Converter.to_dict(existing_model)

        # Apply updates from the dictionary to the model instance
        for field, value in update_data.items():
            if hasattr(existing_model, field):
                setattr(existing_model, field, value)
            else:
                logger.warning(f"Field '{field}' on model {self.model_class.__name__} ignored during update.")

        updated_instance = await self.repository.update(session=session, obj_in=existing_model)
        if updated_instance:
            logger.info(f"{self.model_class.__name__} with ID {entity_id} was updated.")
            # Пропускаем аудит для технических update от бота (только msid)
            skip_audit = (
                audit_context
                and audit_context.get("source") == "bot_service"
                and set(update_data.keys()) <= AUDIT_SKIP_UPDATE_FIELDS
            )
            if not skip_audit:
                await self._write_audit(
                    session, entity_id, "update",
                    old_data=old_data, new_data=Converter.to_dict(updated_instance),
                    audit_context=audit_context,
                )
        return updated_instance

    @db_session_manager
    async def delete(self, *, session, entity_id: Any, **kwargs) -> bool:
        """Deletes an entity by its primary key."""
        audit_context = self._get_audit_context(kwargs)
        existing = await self.repository.get_by_id(session=session, entity_id=entity_id)
        old_data = Converter.to_dict(existing) if existing else None

        result = await self.repository.delete(session=session, entity_id=entity_id)
        if result and old_data is not None:
            await self._write_audit(
                session, entity_id, "delete",
                old_data=old_data, new_data=None,
                audit_context=audit_context,
            )
        return result

    @db_session_manager
    async def find(self, *, session, filters: Dict[str, Any]) -> List[ModelType]:
        """Finds entities that match the given filters."""
        return await self.repository.find(session=session, **filters)