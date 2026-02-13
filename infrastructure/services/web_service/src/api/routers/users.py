import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from shared.clients.database_client import db_client
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.users import UserResponse, CreateUserRequest, UpdateUserBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest):
    response = await db_client.user.create(model_data=body.model_dump())
    if not response.get("success"):
        error = response.get("error", "Failed to create user")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=500),
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
):
    cols = [c.strip() for c in (search_columns or "").split(",") if c.strip()]
    response = await db_client.user.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort),
        search=search or "",
        search_columns=cols if cols else None,
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch users"))
    data = response.get("data", {})
    items = data.get("items", [])
    # Enrich with object (business center) data - batch fetch for reliable names
    object_ids = set(u.get("object_id") for u in items if u.get("object_id"))
    object_map = {}
    if object_ids:
        try:
            page, page_size = 1, 100
            while object_ids - object_map.keys():
                obj_resp = await db_client.object.get_paginated(
                    page=page, page_size=page_size
                )
                if not obj_resp.get("success"):
                    break
                data = obj_resp.get("data", {})
                objs = data.get("items", [])
                if not objs:
                    break
                for obj in objs:
                    oid = obj.get("id")
                    if oid in object_ids and oid not in object_map:
                        name = obj.get("name") or (f"БЦ-{oid}" if oid else "")
                        object_map[oid] = {"id": oid, "name": name}
                total = data.get("total", 0)
                if page * page_size >= total:
                    break
                page += 1
        except Exception as e:
            logger.warning("Failed to batch-fetch objects for enrichment: %s", e)
    for u in items:
        oid = u.get("object_id")
        u["object"] = object_map.get(oid) if oid else None
    return PaginatedResponse(items=items, total=data.get("total", 0))


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
async def update_user(entity_id: int, body: UpdateUserBody):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
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
