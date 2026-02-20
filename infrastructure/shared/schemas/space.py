from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SpaceSchema(BaseModel):
    """Pydantic schema for Space (rental space) entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    object_id: int = 0
    floor: str = ""
    size: float = 0.0
    description: Optional[str] = None
    photos: List[str] = []
    status: str = "FREE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
