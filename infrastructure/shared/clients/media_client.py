"""
MediaClient -- typed proxy for storage_service over HTTP.

Uses HttpRpcClient under the hood. Uploads are performed through
presigned MinIO URLs so file bytes do not travel through RPC as base64.
"""

import logging
import os
from typing import Dict, Any, Optional

import httpx

from shared.clients.http_rpc_client import HttpRpcClient
from shared.utils.media_utils import normalize_public_api_base

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service proxy
# ---------------------------------------------------------------------------

class _MediaProxy:
    """
    Proxy for storage service methods via HTTP RPC.
    Calls /internal/rpc with service="storage" (legacy alias "media" also supported).
    """

    def __init__(self, client: HttpRpcClient, service_name: str):
        self._client = client
        self._service = service_name

    async def _call(self, method: str, **params) -> Dict[str, Any]:
        """Execute an RPC call to the storage service."""
        return await self._client.call(self._service, method, params)

    async def upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file through a presigned MinIO PUT URL.
        This keeps storage_service as the control plane, but the file bytes
        go directly to MinIO instead of traveling through RPC as base64.
        """
        session = await self.create_upload_session(
            filename=filename,
            content_type=content_type,
            size_bytes=len(file_content),
        )
        upload_url = str(
            session.get("internal_upload_url")
            or session.get("upload_url")
            or ""
        ).strip()
        if not upload_url:
            raise RuntimeError("Upload session does not contain a valid URL")

        headers = {
            str(key): str(value)
            for key, value in (session.get("headers") or {}).items()
        }
        if "Content-Type" not in headers and content_type:
            headers["Content-Type"] = content_type

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.request(
                str(session.get("method") or "PUT").upper(),
                upload_url,
                headers=headers,
                content=file_content,
            )
        if not response.is_success:
            raise RuntimeError(
                f"Direct upload failed with status {response.status_code}"
            )

        return await self.complete_upload(
            path=str(session.get("path") or ""),
            original_name=str(session.get("original_name") or filename),
            content_type=str(
                session.get("content_type")
                or content_type
                or "application/octet-stream"
            ),
        )

    async def delete(self, path: str) -> bool:
        """
        Delete a file by path. Returns True if deleted.
        """
        path = path.lstrip("/")
        if path.startswith("media/"):
            path = path[6:].lstrip("/")
        if path.startswith("storage/"):
            path = path[8:].lstrip("/")
        result = await self._call("delete", path=path)
        if not result.get("success"):
            if "not found" in (result.get("error") or "").lower():
                return False
            raise RuntimeError(result.get("error", "Delete failed"))
        return True

    async def create_upload_session(
        self,
        *,
        filename: str,
        content_type: Optional[str] = None,
        size_bytes: int = 0,
    ) -> Dict[str, Any]:
        result = await self._call(
            "create_upload_session",
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=int(size_bytes or 0),
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Failed to create upload session"))
        return result.get("data") or {}

    async def complete_upload(
        self,
        *,
        path: str,
        original_name: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        normalized_path = path.lstrip("/")
        if normalized_path.startswith("media/"):
            normalized_path = normalized_path[6:].lstrip("/")
        if normalized_path.startswith("storage/"):
            normalized_path = normalized_path[8:].lstrip("/")
        result = await self._call(
            "complete_upload",
            path=normalized_path,
            original_name=original_name,
            content_type=content_type or "application/octet-stream",
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Failed to complete upload"))
        data = result.get("data") or {}
        url = data.get("url", "")
        if url and url.startswith("/"):
            data["url"] = self._client.base_url + url
        return data


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class MediaClient:
    """
    Singleton client for storage_service.
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

        base_url = (
            os.getenv("STORAGE_SERVICE_HTTP_URL")
            or os.getenv("MEDIA_SERVICE_HTTP_URL", "http://127.0.0.1:8004")
        ).rstrip("/")
        timeout = float(
            os.getenv("STORAGE_SERVICE_TIMEOUT")
            or os.getenv("MEDIA_SERVICE_TIMEOUT", "30")
        )

        self._http = HttpRpcClient(base_url, timeout=timeout, rpc_path="/internal/rpc")
        self._connected = False

        # Service proxy
        self.storage = _MediaProxy(self._http, "storage")
        self.media = self.storage

        self._is_initialized = True

    async def connect(self) -> None:
        """Open the HTTP connection to storage_service."""
        if self._connected:
            return
        try:
            await self._http.connect()
            self._connected = True
            logger.info("MediaClient connected to storage_service via HTTP.")
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
        """Return the base URL of the storage service."""
        return self._http.base_url

    def get_media_url(self, path: str) -> str:
        """
        Construct full public URL for a stored file.
        Uses PUBLIC_API_BASE_URL / NEXT_PUBLIC_API_URL when set, otherwise internal storage URL.
        """
        path = path.lstrip("/")
        if path.startswith("media/"):
            path = path[6:].lstrip("/")
        if path.startswith("storage/"):
            path = path[8:].lstrip("/")
        base = normalize_public_api_base(os.getenv("PUBLIC_API_BASE_URL", ""))
        if not base:
            base = normalize_public_api_base(os.getenv("NEXT_PUBLIC_API_URL", ""))
        if base:
            return f"{base}/storage/{path}"
        return f"{self._http.base_url}/storage/{path}"

    # --- Convenience methods (delegate to proxy) ---

    async def upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file. Returns {path, url}."""
        return await self.storage.upload(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
        )

    async def delete(self, path: str) -> bool:
        """Delete a file by path. Returns True if deleted."""
        return await self.storage.delete(path=path)

    async def create_upload_session(
        self,
        *,
        filename: str,
        content_type: Optional[str] = None,
        size_bytes: int = 0,
    ) -> Dict[str, Any]:
        """Create a presigned upload session for direct upload to MinIO."""
        return await self.storage.create_upload_session(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    async def complete_upload(
        self,
        *,
        path: str,
        original_name: str,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify uploaded object in MinIO and return normalized payload."""
        return await self.storage.complete_upload(
            path=path,
            original_name=original_name,
            content_type=content_type,
        )

    async def health_check(self) -> bool:
        """Check if the storage service is healthy."""
        return await self._http.health_check()


# Singleton instance for easy import
media_client = MediaClient()
storage_client = media_client
StorageClient = MediaClient
