from typing import List

from pydantic import BaseModel


class ServiceTicketsStatsSchema(BaseModel):
    """Pydantic schema for service ticket statistics."""

    total_count: int = 0
    new_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    new_tickets: List[int] = []
    in_progress_tickets: List[int] = []
    completed_tickets: List[int] = []
