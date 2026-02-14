import logging
from datetime import datetime
from typing import Type, TypeVar, Dict, Optional, List, Any

from sqlalchemy import or_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import Integer, BigInteger, SmallInteger, Float, Numeric, Boolean, DateTime, Date

from database.derived_filters import get_derived_filter

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
RepoType = TypeVar("RepoType")

# Filter operators for get_paginated
FILTER_OPS = {
    "contains": lambda col, v: col.ilike(f"%{v}%"),
    "equals": lambda col, v: col == v,
    "notEquals": lambda col, v: col != v,
    "greaterThan": lambda col, v: col > v,
    "lessThan": lambda col, v: col < v,
    "greaterOrEqual": lambda col, v: col >= v,
    "lessOrEqual": lambda col, v: col <= v,
    "isEmpty": lambda col, _: col.is_(None),
    "isNotEmpty": lambda col, _: col.isnot(None),
}

class GenericRepository:
    """
    A generic repository providing standard CRUD operations for a specific
    SQLAlchemy model. This class should be instantiated for each model.
    """
    def __init__(self, model: Type[ModelType]):
        """
        Initializes the repository for a given SQLAlchemy model.

        Args:
            model: The SQLAlchemy model class this repository will manage.
        """
        self.model = model
        # The primary key column is determined dynamically for generic operations.
        # This assumes a single-column primary key, commonly named 'id'.
        self.pk_column = getattr(self.model, 'id', None)
        if self.pk_column is None:
            logger.warning(
                f"Model {self.model.__name__} does not have an 'id' attribute for PK. "
                f"Operations like get_by_id may fail if not overridden."
            )

    async def create(self, session, *, obj_in: ModelType) -> Optional[ModelType]:
        """
        Creates a new model instance in the database.

        Args:
            session: The active SQLAlchemy async session.
            obj_in: The SQLAlchemy model instance to create.

        Returns:
            The created model instance or None on failure.
        """
        try:
            session.add(obj_in)
            await session.commit()
            await session.refresh(obj_in)
            return obj_in
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}", exc_info=True)
            raise

    async def get_by_id(self, session, *, entity_id: int) -> Optional[ModelType]:
        """
        Retrieves a model instance by its primary key.

        Args:
            session: The active SQLAlchemy async session.
            entity_id: The primary key of the entity.

        Returns:
            The model instance or None if not found.
        """
        if self.pk_column is None:
            logger.error(f"Cannot get by ID: No primary key 'id' found on {self.model.__name__}.")
            raise Exception(f"No primary key 'id' found on {self.model.__name__}.")
        try:
            return await session.get(self.model, entity_id)
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id {entity_id}: {e}", exc_info=True)
            raise

    async def get_all(self, session) -> list[ModelType]:
        """
        Retrieves all instances of the model.

        Args:
            session: The active SQLAlchemy async session.

        Returns:
            A list of all model instances.
        """
        from sqlalchemy.future import select
        try:
            result = await session.execute(select(self.model))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}", exc_info=True)
            raise

    def _coerce_filter_value(self, val, column) -> Any:
        """
        Convert filter value to the appropriate Python type based on SQLAlchemy column type.
        Returns None if coercion fails (e.g. "п" for int column) so the filter is skipped.
        """
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return None
        if column is None:
            return val
        try:
            col_type = column.type
            py_type = getattr(col_type, "python_type", None)
            if py_type is int or isinstance(col_type, (Integer, BigInteger, SmallInteger)):
                return int(float(val))
            if py_type is float or isinstance(col_type, (Float, Numeric)):
                return float(val)
            if py_type is bool or isinstance(col_type, Boolean):
                s = str(val).lower()
                if s in ("1", "true", "yes"): return True
                if s in ("0", "false", "no"): return False
                return None
        except (ValueError, TypeError):
            return None
        return val

    def _apply_filters(self, query, filters: List[Dict[str, Any]], select_stmt):
        """Apply filter conditions to the query. Uses derived filter registry or model columns."""
        for f in filters or []:
            col_id = f.get("columnId") or f.get("column_id")
            op = f.get("operator", "equals")
            val = f.get("value")
            date_from = f.get("dateFrom") or f.get("date_from")
            date_to = f.get("dateTo") or f.get("date_to")
            if not col_id:
                continue

            # Check derived filter registry first
            derived_handler = get_derived_filter(self.model.__name__, col_id)
            if derived_handler is not None:
                try:
                    query = derived_handler(query, self.model, op, val, date_from, date_to)
                except Exception as e:
                    logger.warning(f"Derived filter failed for {self.model.__name__}.{col_id}: {e}")
                continue

            if not hasattr(self.model, col_id):
                continue
            col = getattr(self.model, col_id)
            if op in ("isEmpty", "isNotEmpty"):
                fn = FILTER_OPS.get(op)
                if fn:
                    query = query.where(fn(col, None))
            elif op == "dateRange" and (date_from or date_to):
                try:
                    if date_from:
                        dt_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                        query = query.where(col >= dt_from)
                    if date_to:
                        dt_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                        dt_to_end = dt_to.replace(hour=23, minute=59, second=59, microsecond=999999)
                        query = query.where(col <= dt_to_end)
                except (ValueError, TypeError):
                    pass
            elif val is not None and str(val).strip() != "":
                col_obj = self.model.__table__.columns.get(col_id)
                coerced = self._coerce_filter_value(val, col_obj) if col_obj is not None else val
                if coerced is not None:
                    fn = FILTER_OPS.get(op)
                    if fn:
                        query = query.where(fn(col, coerced))
                elif col_obj is not None and isinstance(col_obj.type, (Integer, BigInteger, SmallInteger, Float, Numeric, Boolean)):
                    # Coercion failed for numeric/bool column (e.g. "pqw" for user_id) — return no results
                    from sqlalchemy.sql.expression import false
                    query = query.where(false())
        return query

    def _apply_search(self, query, search: str, search_columns: List[str]):
        """Apply global search as OR ILIKE across searchable columns. All columns cast to text for ILIKE (integer/datetime etc)."""
        if not search or not search.strip():
            return query
        from sqlalchemy import String, cast
        q = f"%{search.strip()}%"
        clauses = []
        for col_name in search_columns or []:
            if not hasattr(self.model, col_name):
                continue
            col = getattr(self.model, col_name)
            try:
                clauses.append(cast(col, String).ilike(q))
            except Exception:
                pass
        if clauses:
            query = query.where(or_(*clauses))
        return query

    def _apply_sort(self, query, sort: List[Dict[str, Any]]):
        """Apply ORDER BY from sort spec."""
        for s in sort or []:
            col_id = s.get("columnId") or s.get("column_id")
            direction = (s.get("direction") or "asc").lower()
            if not col_id or not hasattr(self.model, col_id):
                continue
            col = getattr(self.model, col_id)
            query = query.order_by(col.desc() if direction == "desc" else col.asc())
        return query

    async def get_paginated(
        self,
        session,
        *,
        page: int = 1,
        page_size: int = 10,
        sort: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        search_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Paginated query with optional sorting, filtering, and global search.
        Returns {items: [...], total: int}.
        """
        from sqlalchemy.future import select
        from sqlalchemy import func as sa_func
        try:
            # Base query
            stmt = select(self.model)
            count_stmt = select(sa_func.count()).select_from(self.model)

            # Apply filters to both
            stmt = self._apply_filters(stmt, filters, stmt)
            count_stmt = self._apply_filters(count_stmt, filters, count_stmt)

            # Apply search to both (default: common text columns)
            default_search_cols = []
            for c in self.model.__table__.columns:
                if hasattr(c.type, "astext") or str(c.type).lower() in ("varchar", "string", "text"):
                    default_search_cols.append(c.key)
            cols = search_columns or default_search_cols
            stmt = self._apply_search(stmt, search, cols)
            count_stmt = self._apply_search(count_stmt, search, cols)

            # Count (without order/limit)
            total_result = await session.execute(count_stmt)
            total = total_result.scalar() or 0

            # Sort and paginate
            stmt = self._apply_sort(stmt, sort)
            offset = max(0, (page - 1) * page_size)
            stmt = stmt.offset(offset).limit(max(1, page_size))

            result = await session.execute(stmt)
            items = result.scalars().all()
            return {"items": items, "total": total}
        except Exception as e:
            logger.error(f"Error in get_paginated {self.model.__name__}: {e}", exc_info=True)
            raise
            
    async def find(self, session, **filters) -> list[ModelType]:
        """
        Finds entities that match the given filters.
        Args:
            session: The active SQLAlchemy session.
            **filters: Keyword arguments for filtering.
        Returns:
            A list of matching SQLAlchemy model instances.
        """
        from sqlalchemy.future import select
        try:
            query = select(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
                else:
                    logger.warning(f"Field {field} does not exist in {self.model.__name__}")
                    raise Exception(f"Field {field} does not exist in {self.model.__name__}")
            result = await session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding {self.model.__name__} by filters {filters}: {e}", exc_info=True)
            raise


    async def update(self, session, *, obj_in: ModelType) -> Optional[ModelType]:
        """
        Updates an existing model instance in the database.
        It uses merge to handle both attached and detached objects.

        Args:
            session: The active SQLAlchemy async session.
            obj_in: The model instance with updated data.

        Returns:
            The updated model instance or None on failure.
        """
        try:
            # Merge updates the object state and re-attaches it to the session.
            updated_obj = await session.merge(obj_in)
            await session.commit()
            await session.refresh(obj_in)
            return updated_obj
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}", exc_info=True)
            raise

    async def delete(self, session, *, entity_id: int) -> bool:
        """
        Deletes a model instance by its primary key.

        Args:
            session: The active SQLAlchemy async session.
            entity_id: The primary key of the entity to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        try:
            obj = await self.get_by_id(session, entity_id=entity_id)
            if obj:
                await session.delete(obj)
                await session.commit()
                return True
            return False
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {entity_id}: {e}", exc_info=True)
            raise

class RepositoryManager:
    """
    Manages the lifecycle and access to all repositories in the application.
    It ensures that for each SQLAlchemy model, a single repository instance is
    created and reused.
    """
    def __init__(self):
        self._repositories: Dict[Type[ModelType], GenericRepository] = {}
        logger.info("RepositoryManager initialized.")

    def register(self, model_class: Type[ModelType]):
        """
        Creates and registers a GenericRepository for a given SQLAlchemy model.
        If a repository for this model already exists, it does nothing.

        Args:
            model_class: The SQLAlchemy model class to be managed.
        """
        if model_class not in self._repositories:
            self._repositories[model_class] = GenericRepository(model=model_class)
            logger.info(f"Registered repository for model: {model_class.__name__}")

    def get(self, model_class: Type[ModelType]) -> GenericRepository:
        """
        Retrieves the repository instance for a specific model.

        Args:
            model_class: The SQLAlchemy model class.

        Returns:
            An instance of GenericRepository for the given model.

        Raises:
            KeyError: If no repository has been registered for the model class.
        """
        if model_class not in self._repositories:
            raise KeyError(f"No repository registered for model {model_class.__name__}. "
                           "Ensure it is registered in DatabaseManager.")
        return self._repositories[model_class]