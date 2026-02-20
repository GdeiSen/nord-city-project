"""Enrichment schemas for embedding in API responses."""
from typing import Optional

from pydantic import BaseModel


class ObjectSummary(BaseModel):
    """Minimal object info for embedding in list responses."""
    id: int
    name: str


class UserSummary(BaseModel):
    """Minimal user info for embedding in list responses."""
    id: int
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    username: str = ""
    object_id: Optional[int] = None
