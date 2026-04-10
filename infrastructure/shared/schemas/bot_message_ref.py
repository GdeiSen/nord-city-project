from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class BotMessageRefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    entity_type: str = ""
    entity_id: int = 0
    chat_id: int = 0
    message_id: int = 0
    kind: str = "PRIMARY"
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
