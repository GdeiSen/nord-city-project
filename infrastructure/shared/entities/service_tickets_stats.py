from pydantic import BaseModel
from typing import List

class ServiceTicketsStats(BaseModel):
    total_count: int
    new_count: int
    in_progress_count: int
    completed_count: int
    new_tickets: List[int]
    in_progress_tickets: List[int]
    completed_tickets: List[int] 