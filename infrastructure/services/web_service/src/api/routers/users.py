import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from shared.clients.database_client import db_client
from shared.permissions import PermissionCodes
from shared.role_deep_links import create_role_start_payload, is_role_deep_link_configured
from shared.schemas.role import RoleSchema
from shared.schemas.user import UserSchema
from api.dependencies import get_current_user, get_audit_context, require_permission
from api.schemas.common import MessageResponse, PaginatedResponse, parse_sort_param
from api.schemas.list_params import parse_list_params_from_query
from api.helpers.paginated_list import create_paginated_list_handler
from api.helpers.enrichment import enrich_users_with_objects
from api.helpers.export_csv import build_csv
from api.schemas.users import UserResponse, CreateUserRequest, UpdateUserBody

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])

EXPORT_MAX_LIMIT = 10_000
USER_EXPORT_HEADERS = {
    "id": "ID",
    "user": "Пользователь",
    "contacts": "Контакты",
    "roles": "Роли",
    "object": "Объект",
    "legal_entity": "Юр. лицо",
    "created": "Создан",
}
class UserRoleLinkItem(BaseModel):
    role_code: str
    role_id: int
    token: str
    title: str
    description: str
    url: str


class UserRoleLinksResponse(BaseModel):
    bot_username: str
    links: List[UserRoleLinkItem]


def _get_env_required(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не задана переменная окружения {name}.",
        )
    return value


def _normalize_bot_username(username: str) -> str:
    return username.strip().lstrip("@")


async def _build_role_links_payload() -> UserRoleLinksResponse:
    if not is_role_deep_link_configured():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не задан защищенный секрет BOT_DEEP_LINK_SECRET или JWT_SECRET_KEY.",
        )
    bot_username = _normalize_bot_username(_get_env_required("BOT_USERNAME"))
    roles_response = await db_client.role.get_all(model_class=RoleSchema)
    if not roles_response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=roles_response.get("error", "Не удалось загрузить роли."),
        )
    roles = sorted(
        roles_response.get("data") or [],
        key=lambda role: (not bool(role.is_system), role.name.casefold(), int(role.id or 0)),
    )

    return UserRoleLinksResponse(
        bot_username=bot_username,
        links=[
            UserRoleLinkItem(
                role_code=role.code,
                role_id=int(role.id),
                token=(token := create_role_start_payload(int(role.id))),
                title=role.name,
                description=role.description or f"Выдает пользователю роль «{role.name}» при запуске бота.",
                url=f"https://t.me/{bot_username}?start={token}",
            )
            for role in roles
            if role.id is not None
        ],
    )


def _get_user_export_value(col_id: str):
    def getter(item: dict):
        if col_id == "id":
            return str(item.get("id", ""))
        if col_id == "user":
            parts = [
                item.get("last_name"),
                item.get("first_name"),
                item.get("middle_name"),
            ]
            name = " ".join(p or "" for p in parts).strip()
            un = item.get("username", "")
            return f"{name} @{un}".strip(" @") if (name or un) else ""
        if col_id == "contacts":
            email = item.get("email", "")
            phone = item.get("phone_number", "")
            return f"{email} {phone}".strip()
        if col_id == "roles":
            roles = item.get("roles") or []
            return ", ".join(str(role.get("name") or role.get("code") or "") for role in roles if isinstance(role, dict))
        if col_id == "object":
            o = item.get("object")
            return o.get("name", f"БЦ-{o.get('id', '')}") if o else ""
        if col_id == "legal_entity":
            return item.get("legal_entity", "")
        if col_id == "created":
            return item.get("created_at", "")
        return str(item.get(col_id, ""))

    return getter


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, PermissionCodes.USERS_MANAGE)
    create_data = body.model_dump()
    response = await db_client.user.create(
        model_data=create_data,
        model_class=UserSchema,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create user")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    user_schema = response["data"]
    items = await enrich_users_with_objects([user_schema])
    return items[0] if items else UserResponse(**user_schema.model_dump())


get_users = create_paginated_list_handler(
    db_client.user,
    model_class=UserSchema,
    enricher=enrich_users_with_objects,
    entity_label="users",
)
router.get("/", response_model=PaginatedResponse[UserResponse])(get_users)


@router.get("/export")
async def export_users(
    search: Optional[str] = None,
    sort: Optional[str] = None,
    search_columns: Optional[str] = None,
    filters: Optional[str] = None,
    columns: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=EXPORT_MAX_LIMIT),
):
    """Export users as CSV. Uses current filters, sort, search. Limited to EXPORT_MAX_LIMIT rows."""
    page, page_size, search_val, sort_val, cols, filter_list = parse_list_params_from_query(
        page=1,
        page_size=limit,
        search=search,
        sort=sort,
        search_columns=search_columns,
        filters=filters,
        max_page_size=None,
    )
    column_ids = [c.strip() for c in (columns or "id,user,contacts,roles,object,legal_entity,created").split(",") if c.strip()]
    column_ids = [c for c in column_ids if c in USER_EXPORT_HEADERS] or list(USER_EXPORT_HEADERS)
    response = await db_client.user.get_paginated(
        page=page,
        page_size=page_size,
        sort=parse_sort_param(sort_val),
        search=search_val,
        search_columns=cols,
        filters=filter_list,
        model_class=UserSchema,
    )
    if not response.get("success"):
        raise HTTPException(status_code=500, detail=response.get("error", "Export failed"))
    data = response.get("data", {})
    items = data.get("items", [])
    items = await enrich_users_with_objects(items)
    items_dicts = [m.model_dump() for m in items]
    value_getters = {c: _get_user_export_value(c) for c in column_ids}
    csv_content = build_csv(items_dicts, column_ids, value_getters, USER_EXPORT_HEADERS)
    utf8_bom = "\ufeff"
    body = (utf8_bom + csv_content).encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="users.csv"'},
    )


@router.get("/role-links", response_model=UserRoleLinksResponse)
async def get_user_role_links(current_user: dict = Depends(get_current_user)):
    require_permission(current_user, PermissionCodes.ROLES_MANAGE)
    return await _build_role_links_payload()


@router.get("/{entity_id}", response_model=UserResponse)
async def get_user_by_id(entity_id: int):
    response = await db_client.user.get_by_id(entity_id=entity_id, model_class=UserSchema)
    if not response.get("success"):
        error = response.get("error", "User not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_schema = response["data"]
    items = await enrich_users_with_objects([user_schema])
    return items[0] if items else UserResponse(**user_schema.model_dump())


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_user(
    entity_id: int,
    body: UpdateUserBody,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    require_permission(current_user, PermissionCodes.USERS_MANAGE)

    # При редактировании себя — исключаем роли из payload, чтобы не потерять доступ.
    if entity_id == current_user["user_id"]:
        update_data.pop("role_ids", None)

    response = await db_client.user.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update user")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="User updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    entity_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, PermissionCodes.USERS_MANAGE)
    response = await db_client.user.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete user")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
