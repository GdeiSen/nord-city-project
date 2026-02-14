"""
Registry for derived/virtual filter handlers.

When a filter targets a column that doesn't exist directly on the model,
or requires custom logic (e.g. join with related table), register a handler here.

Usage:
    from database.derived_filters import register_derived_filter

    def filter_service_ticket_by_user_object(query, model, op, val, date_from, date_to):
        # Custom logic, e.g. filter ServiceTicket by user.object_id
        ...

    register_derived_filter("ServiceTicket", "user_object_id", filter_service_ticket_by_user_object)

Keys: (model.__name__, column_id)
Handler signature: (query, model, op, val, date_from, date_to) -> query
"""
from typing import Callable, Dict, Optional, Tuple, Any

DERIVED_FILTERS: Dict[Tuple[str, str], Callable] = {}


def register_derived_filter(
    model_name: str,
    column_id: str,
    handler: Callable[[Any, Any, str, Any, Any, Any], Any],
) -> None:
    """
    Register a custom filter handler for (model_name, column_id).

    Args:
        model_name: Model class name (e.g. "ServiceTicket").
        column_id: Filter column ID from the request (e.g. "object_id").
        handler: Function(query, model, op, val, date_from, date_to) -> query.
                 Receives the select query, model class, operator, value, date range.
                 Returns the query with the filter applied.
    """
    DERIVED_FILTERS[(model_name, column_id)] = handler


def get_derived_filter(model_name: str, column_id: str) -> Optional[Callable]:
    """Return the registered handler for (model_name, column_id), or None."""
    return DERIVED_FILTERS.get((model_name, column_id))
