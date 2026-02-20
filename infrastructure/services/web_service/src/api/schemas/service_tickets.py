from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from api.schemas.enrichment import ObjectSummary, UserSummary


class ServiceTicketResponse(BaseModel):
    """Response schema for ServiceTicket entity."""
    id: Optional[int] = None
    user_id: int
    object_id: Optional[int] = None
    user: Optional[UserSummary] = None  # Enriched from user_id
    object: Optional[ObjectSummary] = None  # Enriched from object_id (or user's object_id)
    description: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None
    status: str = "NEW"
    ddid: Optional[str] = None
    msid: Optional[int] = None
    answer: Optional[str] = None
    header: Optional[str] = None
    details: Optional[str] = None
    priority: int = 1
    category: Optional[str] = None
    meta: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateServiceTicketRequest(BaseModel):
    """Request body for creating a service ticket. Status is always NEW."""
    model_config = ConfigDict(extra="forbid")

    user_id: int
    object_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None
    status: str = "NEW"  # Ignored: always NEW for new tickets
    ddid: Optional[str] = None
    answer: Optional[str] = None
    header: Optional[str] = None
    details: Optional[str] = None
    priority: int = 1
    category: Optional[str] = None
    msid: Optional[int] = None
    meta: Optional[str] = None


class UpdateServiceTicketBody(BaseModel):
    """Request body for partial service ticket update."""
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[int] = None
    object_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    image: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None  # For status=ASSIGNED: user_id to whom ticket is assigned (stored in meta)
    ddid: Optional[str] = None
    answer: Optional[str] = None
    header: Optional[str] = None
    details: Optional[str] = None
    priority: Optional[int] = None
    category: Optional[str] = None
    msid: Optional[int] = None
    meta: Optional[str] = None


class ServiceTicketsStatsResponse(BaseModel):
    """Response for GET /service-tickets/stats."""
    total_count: int
    new_count: int
    in_progress_count: int
    completed_count: int
    new_tickets: List[int]
    in_progress_tickets: List[int]
    completed_tickets: List[int]
