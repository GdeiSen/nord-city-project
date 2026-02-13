import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.feedbacks import FeedbackResponse, CreateFeedbackRequest, UpdateFeedbackBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedbacks", tags=["Feedbacks"])


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(body: CreateFeedbackRequest):
    response = await db_client.feedback.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create feedback")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=PaginatedResponse[FeedbackResponse])
async def get_feedbacks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
):
    cols = [c.strip() for c in (search_columns or "").split(",") if c.strip()]
    response = await db_client.feedback.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort),
        search=search or "",
        search_columns=cols if cols else None,
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch feedbacks"))
    data = response.get("data", {})
    items = data.get("items", [])
    # Enrich with user data
    user_ids = list({f.get("user_id") for f in items if f.get("user_id")})
    user_map = {}
    for uid in user_ids:
        try:
            ur = await db_client.user.get_by_id(entity_id=uid)
            if ur.get("success") and ur.get("data"):
                user_map[uid] = ur["data"]
        except Exception:
            pass
    for f in items:
        f["user"] = user_map.get(f.get("user_id"), {"first_name": "", "last_name": "", "username": ""})
    return PaginatedResponse(items=items, total=data.get("total", 0))


@router.get("/{entity_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(entity_id: int):
    response = await db_client.feedback.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Feedback not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_feedback(entity_id: int, body: UpdateFeedbackBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.feedback.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Feedback updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(entity_id: int):
    response = await db_client.feedback.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete feedback")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
