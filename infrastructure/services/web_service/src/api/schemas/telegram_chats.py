from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TelegramChatResponse(BaseModel):
    chat_id: int
    title: str = ""
    chat_type: str = "group"
    is_active: bool = True
    bot_status: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
