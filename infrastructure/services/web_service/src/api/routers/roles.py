import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from api.dependencies import get_audit_context, get_current_user, require_permission
from api.schemas.common import MessageResponse
from api.schemas.roles import CreateRoleBody, PermissionResponse, RoleResponse, UpdateRoleBody
from shared.clients.database_client import db_client
from shared.permissions import PermissionCodes, SUPER_ADMIN_ROLE_CODE
from shared.schemas.role import PermissionSchema, RoleSchema

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/roles", tags=["Roles"])


def _require_roles_manage(current_user: dict = Depends(get_current_user)) -> dict:
    require_permission(current_user, PermissionCodes.ROLES_MANAGE)
    return current_user


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(_: dict = Depends(_require_roles_manage)):
    response = await db_client.permission.get_all(model_class=PermissionSchema)
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response.get("error", "Failed to load permissions"))
    return response.get("data") or []


@router.get("/", response_model=list[RoleResponse])
async def list_roles(_: dict = Depends(_require_roles_manage)):
    response = await db_client.role.get_all(model_class=RoleSchema)
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response.get("error", "Failed to load roles"))
    return response.get("data") or []


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: CreateRoleBody,
    request: Request,
    current_user: dict = Depends(_require_roles_manage),
):
    data = body.model_dump()
    permission_ids = data.pop("permission_ids", [])
    data["is_system"] = False
    data["is_default"] = False
    response = await db_client.role.create(
        model_data=data,
        model_class=RoleSchema,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.get("error", "Failed to create role"))
    role = response["data"]
    if getattr(role, "id", None) is not None and permission_ids:
        response = await db_client.role.set_permissions(role_id=int(role.id), permission_ids=permission_ids, model_class=RoleSchema)
        role = response.get("data") if response.get("success") else role
    return role


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: int, _: dict = Depends(_require_roles_manage)):
    response = await db_client.role.get_by_id(entity_id=role_id, model_class=RoleSchema)
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response.get("error", "Failed to load role"))
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return response["data"]


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    body: UpdateRoleBody,
    request: Request,
    current_user: dict = Depends(_require_roles_manage),
):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    existing_response = await db_client.role.get_by_id(entity_id=role_id, model_class=RoleSchema)
    existing = existing_response.get("data") if existing_response.get("success") else None
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if getattr(existing, "code", None) == SUPER_ADMIN_ROLE_CODE:
        update_data.pop("code", None)
        if "permission_ids" in update_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Права роли super_admin управляются системой и не могут быть изменены через интерфейс.",
            )
    response = await db_client.role.update(
        entity_id=role_id,
        update_data=update_data,
        model_class=RoleSchema,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.get("error", "Failed to update role"))
    return response["data"]


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    request: Request,
    current_user: dict = Depends(_require_roles_manage),
):
    existing_response = await db_client.role.get_by_id(entity_id=role_id, model_class=RoleSchema)
    existing = existing_response.get("data") if existing_response.get("success") else None
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if getattr(existing, "is_system", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System roles cannot be deleted")
    response = await db_client.role.delete(
        entity_id=role_id,
        _audit_context=get_audit_context(request, current_user),
    )
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.get("error", "Failed to delete role"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
