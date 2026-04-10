from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ServiceTicketFeedbackRefSchema(BaseModel):
    """One-to-one link between a service ticket and its client feedback."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    service_ticket_id: int
    feedback_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
