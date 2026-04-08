"""Enrichment schemas for embedding in API responses."""
from typing import Optional

from pydantic import BaseModel


class ObjectSummary(BaseModel):
    """Minimal object info for embedding in list responses."""
    id: int
    name: str


class TelegramChatSummary(BaseModel):
    """Minimal Telegram chat info for embedding in API responses."""

    chat_id: int
    title: str = ""
    chat_type: str = "group"
    is_active: bool = True
    bot_status: Optional[str] = None


class UserSummary(BaseModel):
    """Minimal user info for embedding in list responses."""
    id: int
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    username: str = ""
    object_id: Optional[int] = None


class ServiceTicketSummary(BaseModel):
    """Minimal service ticket info for embedding in API responses."""

    id: int
    status: str = "NEW"
    description: str = ""
    object: Optional[ObjectSummary] = None
