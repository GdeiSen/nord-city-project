from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class BotInteractionSessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    session_type: str = ""
    entity_type: str = ""
    entity_id: int = 0
    chat_id: int = 0
    owner_user_id: int = 0
    prompt_message_id: Optional[int] = None
    status: str = "ACTIVE"
    meta: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
