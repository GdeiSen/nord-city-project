from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StorageFileResponse(BaseModel):
    id: int
    storage_path: str
    public_url: str
    original_name: str
    content_type: Optional[str] = None
    extension: Optional[str] = None
    size_bytes: int
    kind: str
    category: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    meta: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
