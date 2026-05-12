from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PermissionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    code: str
    scope: str
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RoleSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    code: str
    name: str
    description: Optional[str] = None
    is_system: bool = False
    is_default: bool = False
    permission_ids: list[int] = []
    permissions: list[PermissionSchema] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserAccessSchema(BaseModel):
    user_id: int
    roles: list[RoleSchema] = []
    permissions: list[str] = []
    is_super_admin: bool = False
