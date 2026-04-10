from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from shared.constants import StorageFileCategory, StorageFileKind


class StorageFileSchema(BaseModel):
    """Transport schema for stored files registered in the system."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    storage_path: str = ""
    public_url: str = ""
    original_name: str = ""
    content_type: Optional[str] = None
    extension: Optional[str] = None
    size_bytes: int = 0
    kind: str = StorageFileKind.OTHER
    category: str = StorageFileCategory.DEFAULT
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    meta: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
