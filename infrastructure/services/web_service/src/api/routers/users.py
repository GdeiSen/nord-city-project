import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from shared.clients.database_client import db_client
from shared.constants import Roles
from shared.schemas.user import UserSchema
from api.dependencies import get_current_user, get_audit_context
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
    "role": "Роль",
    "object": "Объект",
    "legal_entity": "Юр. лицо",
    "created": "Создан",
}
ROLE_LABELS = {
    Roles.GUEST: "Гость",
    Roles.LPR: "User LPR",
    Roles.MA: "User MA",
    Roles.MANAGER: "Менеджер",
    Roles.ADMIN: "Администратор",
    Roles.SUPER_ADMIN: "Super Admin",
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


def _build_role_links_payload() -> UserRoleLinksResponse:
    bot_username = _normalize_bot_username(_get_env_required("BOT_USERNAME"))
    lpr_token = _get_env_required("BOT_DEEP_LINK_LPR_TOKEN", "lpr")
    ma_token = _get_env_required("BOT_DEEP_LINK_MA_TOKEN", "ma")

    return UserRoleLinksResponse(
        bot_username=bot_username,
        links=[
            UserRoleLinkItem(
                role_code="LPR",
                role_id=Roles.LPR,
                token=lpr_token,
                title="Ссылка LPR",
                description=(
                    "Выдает роль LPR для арендаторов: полный пользовательский сценарий "
                    "бота (заявки, опросы, обратная связь и профиль)."
                ),
                url=f"https://t.me/{bot_username}?start={lpr_token}",
            ),
            UserRoleLinkItem(
                role_code="MA",
                role_id=Roles.MA,
                token=ma_token,
                title="Ссылка MA",
                description=(
                    "Выдает роль MA с сокращенным пользовательским меню "
                    "(профиль, обслуживание, гостевая парковка, свободные площади)."
                ),
                url=f"https://t.me/{bot_username}?start={ma_token}",
            ),
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
        if col_id == "role":
            r = item.get("role")
            return ROLE_LABELS.get(r, str(r)) if r is not None else ""
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
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может создавать пользователей.",
        )
    create_data = body.model_dump()
    if create_data.get("role") == Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Назначение роли Super Admin через сайт запрещено. Используйте базу данных.",
        )
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
    column_ids = [c.strip() for c in (columns or "id,user,contacts,role,object,legal_entity,created").split(",") if c.strip()]
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
    if current_user.get("role") != Roles.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только Super Admin может просматривать ссылки ролей.",
        )
    return _build_role_links_payload()


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

    # При редактировании себя — исключаем роль из payload (UI её блокирует, но frontend может отправлять)
    if entity_id == current_user["user_id"]:
        update_data.pop("role", None)

    # Запрет менять свою роль (на случай прямых API-вызовов) — уже убрали выше
    if "role" in update_data:
        new_role = update_data["role"]
        target_user_response = await db_client.user.get_by_id(
            entity_id=entity_id,
            model_class=UserSchema,
        )
        if not target_user_response.get("success") or target_user_response.get("data") is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        target_user = target_user_response["data"]

        # Роль Super Admin управляется только через БД: запрещаем назначения и снятие через web.
        if new_role == Roles.SUPER_ADMIN or target_user.role == Roles.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Управление ролью Super Admin через сайт запрещено. Используйте базу данных.",
            )

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
    response = await db_client.user.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete user")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
