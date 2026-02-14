"""
Pydantic schemas for list/pagination requests.
Unified contract for filtering, sorting, and pagination across all list endpoints.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FilterOperator(str, Enum):
    """Supported filter operators."""
    equals = "equals"
    notEquals = "notEquals"
    contains = "contains"
    greaterThan = "greaterThan"
    lessThan = "lessThan"
    greaterOrEqual = "greaterOrEqual"
    lessOrEqual = "lessOrEqual"
    dateRange = "dateRange"
    isEmpty = "isEmpty"
    isNotEmpty = "isNotEmpty"


class FilterItem(BaseModel):
    """Single filter condition."""
    columnId: str = Field(..., min_length=1)
    operator: FilterOperator
    value: Optional[str] = None
    dateFrom: Optional[str] = None
    dateTo: Optional[str] = None

    class Config:
        extra = "forbid"


def parse_list_params_from_query(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
    filters: Optional[str] = None,
) -> tuple[int, int, str, str, Optional[list[str]], Optional[list[dict]]]:
    """
    Parse and validate list params from query string.
    Returns (page, page_size, search, sort, search_columns_list, filters_list).
    """
    import json

    cols = [c.strip() for c in (search_columns or "").split(",") if c.strip()] or None
    filter_list = None
    if filters:
        try:
            raw = json.loads(filters)
            if isinstance(raw, list):
                valid = []
                for item in raw:
                    try:
                        if isinstance(item, dict):
                            valid.append(FilterItem(**item).model_dump())
                    except Exception:
                        pass
                filter_list = valid if valid else None
        except (json.JSONDecodeError, ValueError, TypeError):
            filter_list = None

    return (
        max(1, page),
        min(500, max(1, page_size)),
        search or "",
        sort or "",
        cols,
        filter_list,
    )
