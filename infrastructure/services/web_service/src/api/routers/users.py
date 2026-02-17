import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status

from shared.clients.database_client import db_client
from shared.constants import Roles
from api.dependencies import get_current_user
from api.schemas.common import MessageResponse, PaginatedResponse
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_users_with_objects
from api.schemas.users import UserResponse, CreateUserRequest, UpdateUserBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может создавать пользователей.",
        )
    create_data = body.model_dump()
    if create_data.get("role") == Roles.SUPER_ADMIN:
        if current_user.get("role") != Roles.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только Super Admin может создавать пользователей с ролью Super Admin.",
            )
    response = await db_client.user.create(model_data=create_data)
    if not response.get("success"):
        error = response.get("error", "Failed to create user")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


get_users = create_paginated_list_handler(
    db_client.user,
    enricher=enrich_users_with_objects,
    entity_label="users",
)
router.get("/", response_model=PaginatedResponse[UserResponse])(get_users)


@router.get("/{entity_id}", response_model=UserResponse)
async def get_user_by_id(entity_id: int):
    response = await db_client.user.get_by_id(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "User not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_user(
    entity_id: int,
    body: UpdateUserBody,
    current_user: dict = Depends(get_current_user),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Запрет менять свою роль (риск потери доступа)
    if "role" in update_data:
        if entity_id == current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нельзя изменить свою роль.",
            )
        new_role = update_data["role"]
        current_role = current_user.get("role")
        # Администратор не может назначать роль Super Admin
        if new_role == Roles.SUPER_ADMIN and current_role != Roles.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Только Super Admin может назначать роль Super Admin.",
            )

    response = await db_client.user.update(entity_id=entity_id, update_data=update_data)
    if not response.get("success"):
        error = response.get("error", "Failed to update user")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="User updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(entity_id: int):
    response = await db_client.user.delete(entity_id=entity_id)
    if not response.get("success"):
        error = response.get("error", "Failed to delete user")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
