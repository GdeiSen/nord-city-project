from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ContractSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    number: str
    title: Optional[str] = None
    status: str = "ACTIVE"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
