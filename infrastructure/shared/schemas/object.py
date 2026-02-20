from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class ObjectSchema(BaseModel):
    """Pydantic schema for Object (rental object) entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str = ""
    address: str = ""
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("photos", mode="before")
    @classmethod
    def normalize_photos(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []
