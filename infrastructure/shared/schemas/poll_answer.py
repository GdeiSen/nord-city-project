from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PollAnswerSchema(BaseModel):
    """Pydantic schema for PollAnswer entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: int = 0
    ddid: str = ""
    answer: str = ""
    meta: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
