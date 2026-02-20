from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ServiceTicketSchema(BaseModel):
    """Pydantic schema for ServiceTicket entity. Mirrors ORM."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: int = 0
    object_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None
    status: str = "NEW"
    priority: int = 1
    category: Optional[str] = None
    ddid: str = ""
    msid: Optional[int] = None
    meta: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
