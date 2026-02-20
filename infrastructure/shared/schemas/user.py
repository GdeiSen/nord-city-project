from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserSchema(BaseModel):
    """Pydantic schema for User entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: int
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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
