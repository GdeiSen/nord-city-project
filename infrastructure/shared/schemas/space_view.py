from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SpaceViewSchema(BaseModel):
    """Pydantic schema for SpaceView entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    space_id: int = 0
    user_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
