"""
MediaClient -- typed proxy for media_service over HTTP.

Uses HttpRpcClient under the hood. Provides explicit methods for
upload, delete, and URL construction. Follows the same pattern as
DatabaseClient and BotClient.
"""

import base64
import os
import logging
from typing import Dict, Any, Optional

from shared.clients.http_rpc_client import HttpRpcClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service proxy
# ---------------------------------------------------------------------------

class _MediaProxy:
    """
    Proxy for media service methods via HTTP RPC.
    Calls /internal/rpc with service="media".
    """

    def __init__(self, client: HttpRpcClient, service_name: str):
        self._client = client
        self._service = service_name

    async def _call(self, method: str, **params) -> Dict[str, Any]:
        """Execute an RPC call to the media service."""
        return await self._client.call(self._service, method, params)

    async def upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file. Params: file_content_b64, filename, content_type.
        Returns {path, url} — url is relative; client adds base_url for full URL.
        """
        file_content_b64 = base64.b64encode(file_content).decode("ascii")
        result = await self._call(
            "upload",
            file_content_b64=file_content_b64,
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Upload failed"))
        data = result.get("data") or {}
        # Ensure url is full URL for external use
        base_url = self._client.base_url
        url = data.get("url", "")
        if url and url.startswith("/"):
            data["url"] = base_url + url
        return data

    async def delete(self, path: str) -> bool:
        """
        Delete a file by path. Returns True if deleted.
        """
        path = path.lstrip("/")
        if path.startswith("media/"):
            path = path[6:].lstrip("/")
        result = await self._call("delete", path=path)
        if not result.get("success"):
            if "not found" in (result.get("error") or "").lower():
                return False
            raise RuntimeError(result.get("error", "Delete failed"))
        return True


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class MediaClient:
    """
    Singleton client for media_service.
    Uses HttpRpcClient and exposes media proxy.
    """

    _instance: Optional["MediaClient"] = None
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return

        base_url = os.getenv("MEDIA_SERVICE_HTTP_URL", "http://127.0.0.1:8004").rstrip("/")
        timeout = float(os.getenv("MEDIA_SERVICE_TIMEOUT", "30"))

        self._http = HttpRpcClient(base_url, timeout=timeout, rpc_path="/internal/rpc")
        self._connected = False

        # Service proxy
        self.media = _MediaProxy(self._http, "media")

        self._is_initialized = True

    async def connect(self) -> None:
        """Open the HTTP connection to media_service."""
        if self._connected:
            return
        try:
            await self._http.connect()
            self._connected = True
            logger.info("MediaClient connected to media_service via HTTP.")
        except Exception as e:
            logger.error(f"Failed to connect MediaClient: {e}", exc_info=True)
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close the HTTP connection."""
        if self._connected:
            await self._http.disconnect()
            self._connected = False
            logger.info("MediaClient disconnected.")

    def get_base_url(self) -> str:
        """Return the base URL of the media service."""
        return self._http.base_url

    def get_media_url(self, path: str) -> str:
        """
        Construct full public URL for a stored media file.
        """
        path = path.lstrip("/")
        if path.startswith("media/"):
            path = path[6:].lstrip("/")
        return f"{self._http.base_url}/media/{path}"

    # --- Convenience methods (delegate to proxy) ---

    async def upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file. Returns {path, url}."""
        return await self.media.upload(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
        )

    async def delete(self, path: str) -> bool:
        """Delete a file by path. Returns True if deleted."""
        return await self.media.delete(path=path)

    async def health_check(self) -> bool:
        """Check if the media service is healthy."""
        return await self._http.health_check()


# Singleton instance for easy import
media_client = MediaClient()
