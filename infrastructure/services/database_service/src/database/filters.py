"""
Centralized filter and search registry for virtual/composite columns.

Handlers are registered by (model_name, column_id). Used by GenericRepository
for _apply_filters and _apply_search.
"""
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Tuple

from sqlalchemy import or_, cast, String
from sqlalchemy.sql.expression import false

# ---------------------------------------------------------------------------
# Base handler
# ---------------------------------------------------------------------------


class FilterHandler(ABC):
    """Abstract base for filter handlers."""

    @abstractmethod
    def apply(
        self,
        query: Any,
        model: Any,
        op: str,
        val: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Any:
        """Apply filter to query. Returns modified query."""

    def get_search_columns(self) -> Optional[List[str]]:
        """Return DB column names for search expansion, or None if not applicable."""
        return None


# ---------------------------------------------------------------------------
# Composite text columns (e.g. user = first_name + last_name + username)
# ---------------------------------------------------------------------------


class CompositeTextFilter(FilterHandler):
    """Filter across multiple text columns with OR logic."""

    def __init__(self, columns: List[str]) -> None:
        self._columns = columns

    def apply(
        self,
        query: Any,
        model: Any,
        op: str,
        val: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Any:
        text_cols = [
            getattr(model, c) for c in self._columns if hasattr(model, c)
        ]
        if not text_cols:
            return query.where(false())

        if op in ("isEmpty", "isNotEmpty"):
            from sqlalchemy import and_ as _and
            if op == "isEmpty":
                return query.where(_and(*(c.is_(None) for c in text_cols)))
            return query.where(or_(*(c.isnot(None) for c in text_cols)))

        if not val or not str(val).strip():
            return query.where(false())
        val_str = str(val).strip()
        q = f"%{val_str}%"

        if op in ("equals", "contains"):
            clauses = [cast(c, String).ilike(q) for c in text_cols]
            return query.where(or_(*clauses))
        if op == "notEquals":
            clauses = [cast(c, String).ilike(q) for c in text_cols]
            return query.where(~or_(*clauses))
        if op == "matchesRegex":
            try:
                re.compile(val_str)
            except re.error:
                return query.where(false())
            clauses = [cast(c, String).op("~*")(val_str) for c in text_cols]
            return query.where(or_(*clauses))

        return query

    def get_search_columns(self) -> List[str]:
        return list(self._columns)


# ---------------------------------------------------------------------------
# Audit action aliases
# ---------------------------------------------------------------------------


class AuditActionFilter(FilterHandler):
    """Filter audit actions with support for legacy and grouped action names."""

    _ALIASES = {
        "create": ["create"],
        "update": ["update", "edit"],
        "edit": ["update", "edit"],
        "delete": ["delete"],
        "send": ["send"],
        "sync": ["sync"],
        "reroute": ["reroute"],
        "pin": ["pin"],
    }

    def apply(
        self,
        query: Any,
        model: Any,
        op: str,
        val: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Any:
        if not hasattr(model, "action"):
            return query.where(false())

        col = getattr(model, "action")

        if op == "isEmpty":
            return query.where(col.is_(None))
        if op == "isNotEmpty":
            return query.where(col.isnot(None))
        if val is None or not str(val).strip():
            return query.where(false())

        raw_values = [item.strip().lower() for item in str(val).split(",") if item.strip()]
        if not raw_values:
            return query.where(false())

        expanded_values: list[str] = []
        for raw in raw_values:
            expanded_values.extend(self._ALIASES.get(raw, [raw]))
        unique_values = list(dict.fromkeys(expanded_values))

        if op == "equals":
            return query.where(col.in_(unique_values))
        if op == "notEquals":
            return query.where(~col.in_(unique_values))
        if op == "contains":
            clauses = [cast(col, String).ilike(f"%{value}%") for value in unique_values]
            return query.where(or_(*clauses))

        return query

    def get_search_columns(self) -> List[str]:
        return ["action"]


# ---------------------------------------------------------------------------
# Custom function handler (for joins, complex logic)
# ---------------------------------------------------------------------------


class CustomFilter(FilterHandler):
    """Handler that delegates to a custom function."""

    def __init__(self, fn: Callable[[Any, Any, str, Any, Any, Any], Any]) -> None:
        self._fn = fn

    def apply(
        self,
        query: Any,
        model: Any,
        op: str,
        val: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Any:
        return self._fn(query, model, op, val, date_from, date_to)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class FilterRegistry:
    """Central registry for model column filter handlers."""

    def __init__(self) -> None:
        self._handlers: dict[Tuple[str, str], FilterHandler] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in composite column handlers."""
        self.register("User", "user", CompositeTextFilter(
            ["first_name", "last_name", "middle_name", "username"]
        ))
        self.register("User", "contacts", CompositeTextFilter(
            ["email", "phone_number"]
        ))
        self.register("AuditLog", "action", AuditActionFilter())

    def register(self, model_name: str, column_id: str, handler: FilterHandler) -> None:
        """Register a handler for (model_name, column_id)."""
        self._handlers[(model_name, column_id)] = handler

    def register_custom(
        self,
        model_name: str,
        column_id: str,
        fn: Callable[[Any, Any, str, Any, Any, Any], Any],
    ) -> None:
        """Register a custom function handler."""
        self.register(model_name, column_id, CustomFilter(fn))

    def get_handler(self, model_name: str, column_id: str) -> Optional[FilterHandler]:
        """Return the handler for (model_name, column_id), or None."""
        return self._handlers.get((model_name, column_id))

    def apply_filter(
        self,
        query: Any,
        model: Any,
        column_id: str,
        op: str,
        val: Any,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Tuple[Any, bool]:
        """
        Apply filter if a handler exists.
        Returns (modified_query, True) if applied, (query, False) otherwise.
        """
        handler = self.get_handler(model.__name__, column_id)
        if handler is None:
            return query, False
        return handler.apply(query, model, op, val, date_from, date_to), True

    def get_search_columns(self, model_name: str, column_id: str) -> Optional[List[str]]:
        """
        For virtual columns, return DB column names to search in.
        Returns None if column should be used as-is (regular DB column).
        """
        handler = self.get_handler(model_name, column_id)
        if handler is None:
            return None
        return handler.get_search_columns()


# Singleton registry
registry = FilterRegistry()


def register_custom(
    model_name: str,
    column_id: str,
    fn: Callable[[Any, Any, str, Any, Any, Any], Any],
) -> None:
    """Register a custom filter handler. Use when composite columns are not enough."""
    registry.register_custom(model_name, column_id, fn)
