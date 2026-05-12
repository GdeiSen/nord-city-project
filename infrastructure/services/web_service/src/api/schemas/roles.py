from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    id: int
    code: str
    scope: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    is_default: bool = False
    permission_ids: list[int] = []
    permissions: list[PermissionResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    name: str
    description: Optional[str] = None
    permission_ids: list[int] = []


class UpdateRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[int]] = None
