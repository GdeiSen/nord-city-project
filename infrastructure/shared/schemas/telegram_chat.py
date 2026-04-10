from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class TelegramChatSchema(BaseModel):
    """Pydantic schema for TelegramChat entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    chat_id: int
    title: str = ""
    chat_type: str = "group"
    is_active: bool = True
    bot_status: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    meta: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
