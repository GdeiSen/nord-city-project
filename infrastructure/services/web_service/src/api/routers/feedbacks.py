import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from shared.clients.database_client import db_client
from shared.constants import FeedbackTypes, Roles
from shared.schemas.feedback import FeedbackSchema
from api.dependencies import get_current_user, get_audit_context
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_feedbacks_with_users
from api.helpers.export_csv import build_csv
from api.schemas.feedbacks import FeedbackResponse, CreateFeedbackRequest, UpdateFeedbackBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])

EXPORT_MAX_LIMIT = 10_000
FEEDBACK_EXPORT_HEADERS = {
    "id": "ID",
    "type": "Тип",
    "ticket": "Заявка",
    "user": "Пользователь",
    "feedback": "Отзыв",
    "date": "Дата",
}


def _get_feedback_export_value(col_id: str):
    def getter(item: dict):
        if col_id == "id":
            return str(item.get("id", ""))
        if col_id == "type":
            feedback_type = item.get("feedback_type", FeedbackTypes.GENERAL)
            return "Отзыв на заявку" if feedback_type == FeedbackTypes.SERVICE_TICKET else "Общий отзыв"
        if col_id == "ticket":
            ticket = item.get("service_ticket") or {}
            ticket_id = item.get("service_ticket_id") or ticket.get("id")
            return f"#{ticket_id}" if ticket_id else ""
        if col_id == "user":
            u = item.get("user") or {}
            parts = [u.get("last_name"), u.get("first_name"), u.get("middle_name")]
            name = " ".join(p or "" for p in parts).strip()
            un = u.get("username", "")
            return f"{name} @{un}".strip(" @") if (name or un) else ""
        if col_id == "feedback":
            answer = item.get("answer", "")
            text = item.get("text", "")
            return f"{answer} | {text}".strip(" |") if (answer or text) else ""
        if col_id == "date":
            return item.get("created_at", "")
        return str(item.get(col_id, ""))

    return getter


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: CreateFeedbackRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может создавать отзывы.",
        )
    if body.feedback_type == FeedbackTypes.SERVICE_TICKET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отзывы на заявки создаются автоматически ботом.",
        )
    response = await db_client.feedback.create(
        model_data=body.model_dump(),
        model_class=FeedbackSchema,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create feedback")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    feedback_schema = response["data"]
    items = await enrich_feedbacks_with_users([feedback_schema])
    return items[0] if items else FeedbackResponse(**feedback_schema.model_dump())


get_feedbacks = create_paginated_list_handler(
    db_client.feedback,
    model_class=FeedbackSchema,
    enricher=enrich_feedbacks_with_users,
    entity_label="feedbacks",
)
router.get("/", response_model=PaginatedResponse[FeedbackResponse])(get_feedbacks)


@router.get("/export")
async def export_feedbacks(
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
    filters: Optional[str] = None,
    columns: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=EXPORT_MAX_LIMIT),
):
    """Export feedbacks as CSV. Uses current filters, sort, search. Limited to EXPORT_MAX_LIMIT rows."""
    page, page_size, search_val, sort_val, cols, filter_list = parse_list_params_from_query(
        page=1,
        page_size=limit,
        search=search,
        sort=sort,
        search_columns=search_columns,
        filters=filters,
        max_page_size=None,
    )
    column_ids = [c.strip() for c in (columns or "id,type,ticket,user,feedback,date").split(",") if c.strip()]
    column_ids = [c for c in column_ids if c in FEEDBACK_EXPORT_HEADERS] or list(FEEDBACK_EXPORT_HEADERS)
    response = await db_client.feedback.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort_val),
        search=search_val,
        search_columns=cols,
        filters=filter_list,
        model_class=FeedbackSchema,
    )
    if not response.get("success"):
        raise HTTPException(status_code=500, detail=response.get("error", "Export failed"))
    data = response.get("data", {})
    items = data.get("items", [])
    items = await enrich_feedbacks_with_users(items)
    items_dicts = [m.model_dump() for m in items]
    value_getters = {c: _get_feedback_export_value(c) for c in column_ids}
    csv_content = build_csv(items_dicts, column_ids, value_getters, FEEDBACK_EXPORT_HEADERS)
    utf8_bom = "\ufeff"
    body = (utf8_bom + csv_content).encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="feedbacks.csv"'},
    )


@router.get("/service-ticket/{service_ticket_id}", response_model=Optional[FeedbackResponse])
async def get_feedback_by_service_ticket_id(service_ticket_id: int):
    response = await db_client.feedback.get_by_service_ticket_id(
        service_ticket_id=service_ticket_id,
        model_class=FeedbackSchema,
    )
    if not response.get("success"):
        error = response.get("error", "Failed to load service ticket feedback")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    feedback_schema = response.get("data")
    if feedback_schema is None:
        return None
    items = await enrich_feedbacks_with_users([feedback_schema])
    return items[0] if items else FeedbackResponse(**feedback_schema.model_dump())


@router.get("/{entity_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(entity_id: int):
    response = await db_client.feedback.get_by_id(entity_id=entity_id, model_class=FeedbackSchema)
    if not response.get("success"):
        error = response.get("error", "Feedback not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    feedback_schema = response["data"]
    items = await enrich_feedbacks_with_users([feedback_schema])
    return items[0] if items else FeedbackResponse(**feedback_schema.model_dump())


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_feedback(
    entity_id: int,
    body: UpdateFeedbackBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может редактировать отзывы.",
        )
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    existing = await db_client.feedback.get_by_id(entity_id=entity_id, model_class=FeedbackSchema)
    if not existing.get("success"):
        error = existing.get("error", "Feedback not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    existing_feedback = existing.get("data")
    if existing_feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    if existing_feedback.feedback_type == FeedbackTypes.SERVICE_TICKET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Отзывы на заявки нельзя редактировать вручную.",
        )
    if update_data.get("feedback_type") == FeedbackTypes.SERVICE_TICKET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отзывы на заявки создаются автоматически ботом.",
        )
    response = await db_client.feedback.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Feedback updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    entity_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может удалять отзывы.",
        )
    existing = await db_client.feedback.get_by_id(entity_id=entity_id, model_class=FeedbackSchema)
    if not existing.get("success"):
        error = existing.get("error", "Feedback not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    existing_feedback = existing.get("data")
    if existing_feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    if existing_feedback.feedback_type == FeedbackTypes.SERVICE_TICKET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Отзывы на заявки нельзя удалять вручную.",
        )
    response = await db_client.feedback.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
