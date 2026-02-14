"""
Factory for paginated list handlers.
Eliminates duplicated boilerplate across list endpoints that use
parse_list_params_from_query, db_client.get_paginated, and enrichment.
"""
import logging
from typing import Callable, Awaitable, Optional, Any

from fastapi import HTTPException, Query

from api.schemas.common import PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query

logger = logging.getLogger(__name__)

# Type for async enricher: receives items (list of dicts), mutates in place
Enricher = Callable[[list], Awaitable[None]]


def create_paginated_list_handler(
    entity_proxy: Any,
    *,
    enricher: Optional[Enricher] = None,
    entity_label: str = "items",
) -> Callable:
    """
    Create a FastAPI-compatible handler for paginated list endpoints.

    Args:
        entity_proxy: db_client proxy (e.g. db_client.user, db_client.service_ticket).
        enricher: Optional async function(items) that enriches items in place.
        entity_label: Label for error messages (e.g. "users", "service tickets").

    Returns:
        Async function suitable for use as router handler.
    """

    async def handler(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=500),
        search: Optional[str] = None,
        sort: Optional[str] = None,
        search_columns: Optional[str] = None,
        filters: Optional[str] = None,
    ):
        page, page_size, search, sort, cols, filter_list = parse_list_params_from_query(
            page=page,
            page_size=page_size,
            search=search,
            sort=sort,
            search_columns=search_columns,
            filters=filters,
        )
        response = await entity_proxy.get_paginated(
            page=page,
            page_size=page_size,
            sort=parse_sort_param(sort),
            search=search,
            search_columns=cols,
            filters=filter_list,
        )
        if not response.get("success"):
            raise HTTPException(
                status_code=500,
                detail=response.get("error", f"Failed to fetch {entity_label}"),
            )
        data = response.get("data", {})
        items = data.get("items", [])
        if enricher:
            await enricher(items)
        return PaginatedResponse(items=items, total=data.get("total", 0))

    return handler
