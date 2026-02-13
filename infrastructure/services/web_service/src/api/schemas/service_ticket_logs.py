from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ServiceTicketLogResponse(BaseModel):
    """Response schema for ServiceTicketLog entity."""
    id: Optional[int] = None
    ticket_id: int
    status: str
    user_id: Optional[int] = None
    assignee: Optional[str] = None
    msid: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class CreateLogRequest(BaseModel):
    """Request body for creating a service ticket log entry."""
    model_config = ConfigDict(extra="forbid")

    ticket_id: int
    status: str
    user_id: Optional[int] = None
    assignee: Optional[str] = None
    msid: Optional[int] = None
    comment: Optional[str] = None


class UpdateLogBody(BaseModel):
    """Request body for partial service ticket log update."""
    model_config = ConfigDict(extra="forbid")

    ticket_id: Optional[int] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    assignee: Optional[str] = None
    msid: Optional[int] = None
    comment: Optional[str] = None
