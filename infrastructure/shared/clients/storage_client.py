"""
Preferred storage client import.

Kept as a thin alias over the legacy media_client module so the current
deployment can migrate gradually without breaking older imports.
"""

from .media_client import MediaClient as StorageClient
from .media_client import media_client as storage_client

__all__ = ["StorageClient", "storage_client"]
