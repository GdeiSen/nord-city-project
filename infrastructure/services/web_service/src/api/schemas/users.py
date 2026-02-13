from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ObjectSummary(BaseModel):
    """Minimal object info for embedding in list responses."""
    id: int
    name: str


class UserResponse(BaseModel):
    """Response schema for User entity. Matches web/types/index.ts User interface."""
    id: int
    username: Optional[str] = None
    role: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    language_code: str = "ru"
    data_processing_consent: bool = False
    object_id: Optional[int] = None
    object: Optional[ObjectSummary] = None  # Enriched from object_id
    legal_entity: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateUserRequest(BaseModel):
    """Request body for creating a user. Matches Omit<User, 'id'|'created_at'|'updated_at'>."""
    model_config = ConfigDict(extra="forbid")

    id: int  # Telegram user ID — set by the client, not auto-generated
    username: Optional[str] = None
    role: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    language_code: str = "ru"
    data_processing_consent: bool = False
    object_id: Optional[int] = None
    legal_entity: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None


class UpdateUserBody(BaseModel):
    """Request body for partial user update. All fields optional (Partial<User>)."""
    model_config = ConfigDict(extra="forbid")

    username: Optional[str] = None
    role: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    language_code: Optional[str] = None
    data_processing_consent: Optional[bool] = None
    object_id: Optional[int] = None
    legal_entity: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
