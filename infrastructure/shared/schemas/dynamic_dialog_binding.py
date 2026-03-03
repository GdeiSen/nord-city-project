from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DynamicDialogBindingSchema(BaseModel):
    """Canonical DDID registry entry."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    ddid: str = ""
    dialog_id: int = 0
    sequence_id: int = 0
    item_id: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
