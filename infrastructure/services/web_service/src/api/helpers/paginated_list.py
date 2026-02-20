"""
Factory for paginated list handlers.
Eliminates duplicated boilerplate across list endpoints that use
parse_list_params_from_query, db_client.get_paginated, and enrichment.
"""
import logging
from typing import Callable, Awaitable, Optional, Any, Type

from fastapi import HTTPException, Query

from shared.utils.converter import Converter

from api.schemas.common import PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query

logger = logging.getLogger(__name__)

# Enricher: receives list of models, returns list of response schemas
Enricher = Callable[[list], Awaitable[list]]


def create_paginated_list_handler(
    entity_proxy: Any,
    *,
    model_class: Optional[Type[Any]] = None,
    enricher: Optional[Enricher] = None,
    response_schema: Optional[Type[Any]] = None,
    entity_label: str = "items",
) -> Callable:
    """
    Create a FastAPI-compatible handler for paginated list endpoints.

    Args:
        entity_proxy: db_client proxy (e.g. db_client.user, db_client.service_ticket).
        model_class: Optional model class for deserialising items from db_client.
        enricher: Optional async function(items) that converts models to response schemas.
        response_schema: When no enricher, convert each model to this schema (e.g. SpaceViewResponse).
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
            search=search or "",
            search_columns=cols,
            filters=filter_list,
            model_class=model_class,
        )
        if not response.get("success"):
            raise HTTPException(
                status_code=500,
                detail=response.get("error", f"Failed to fetch {entity_label}"),
            )
        data = response.get("data", {})
        items = data.get("items", [])
        if enricher:
            items = await enricher(items)
        elif response_schema and items:
            items = [response_schema(**Converter.to_dict(m)) for m in items]
        return PaginatedResponse(items=items, total=data.get("total", 0))

    return handler
