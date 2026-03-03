from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, JSON, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.constants import StorageFileCategory, StorageFileKind

from .base import Base


class StorageFile(Base):
    __tablename__ = "storage_files"

    id: Mapped[int] = mapped_column(
        Integer,
        Sequence("storage_files_id_seq"),
        primary_key=True,
    )
    storage_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    public_url: Mapped[str] = mapped_column(String(1000))
    original_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(255))
    extension: Mapped[Optional[str]] = mapped_column(String(32))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    kind: Mapped[str] = mapped_column(String(32), default=StorageFileKind.OTHER, index=True)
    category: Mapped[str] = mapped_column(
        String(32),
        default=StorageFileCategory.DEFAULT,
        index=True,
    )
    entity_type: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    entity_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
