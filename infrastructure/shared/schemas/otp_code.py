from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OtpCodeSchema(BaseModel):
    """Pydantic schema for OtpCode entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: int = 0
    code: str = ""
    is_used: bool = False
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
