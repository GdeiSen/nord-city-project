import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request, Response, status

from shared.clients.database_client import db_client
from shared.schemas.poll_answer import PollAnswerSchema
from api.dependencies import get_audit_context, get_optional_current_user
from api.schemas.common import MessageResponse
from api.schemas.polls import PollAnswerResponse, CreatePollRequest, UpdatePollBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/polls", tags=["Polls"])


@router.post("/", response_model=PollAnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(body: CreatePollRequest, request: Request):
    response = await db_client.poll.create(
        model_data=body.model_dump(),
        model_class=PollAnswerSchema,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create poll answer")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[PollAnswerResponse])
async def get_all_polls():
    response = await db_client.poll.get_all(model_class=PollAnswerSchema)
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch poll answers"))
    return response.get("data", [])


@router.get("/{entity_id}", response_model=PollAnswerResponse)
async def get_poll_by_id(entity_id: int):
    response = await db_client.poll.get_by_id(
        entity_id=entity_id,
        model_class=PollAnswerSchema,
    )
    if not response.get("success"):
        error = response.get("error", "Poll answer not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll answer not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_poll(entity_id: int, body: UpdatePollBody, request: Request):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.poll.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update poll answer")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Poll answer updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(entity_id: int, request: Request):
    response = await db_client.poll.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete poll answer")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
