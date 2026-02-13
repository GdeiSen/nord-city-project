"""
HTTP RPC Client for inter-service communication.

This module provides a lightweight HTTP client that sends JSON RPC-style
requests to a service endpoint (e.g. database_service POST /internal/rpc).
It does not know about domain types; it only transmits and receives dicts.
"""

import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


class HttpRpcClient:
    """
    Generic HTTP client for calling internal RPC endpoints.

    Usage:
        client = HttpRpcClient("http://127.0.0.1:8001")
        result = await client.call("user", "get_all", {})
        # result == {"success": True, "data": [...], "error": None}
    """

    def __init__(self, base_url: str, *, timeout: float = 30.0, rpc_path: str = "/internal/rpc"):
        """
        Args:
            base_url: Base URL of the target service (e.g. http://127.0.0.1:8001).
            timeout: Request timeout in seconds.
            rpc_path: Path to the RPC endpoint on the target service.
        """
        self.base_url = base_url.rstrip("/")
        self.rpc_url = f"{self.base_url}{rpc_path}"
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Create the underlying httpx AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info(f"HttpRpcClient connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Close the underlying httpx AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("HttpRpcClient disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    async def call(self, service: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an RPC request to the target service.

        Args:
            service: Service name (e.g. "user", "service_ticket").
            method: Method name (e.g. "get_all", "create").
            params: Parameters dict to pass to the method.

        Returns:
            Dict with keys: success (bool), data (Any), error (str | None).
        """
        if self._client is None:
            raise ConnectionError("HttpRpcClient is not connected. Call connect() first.")

        payload = {"service": service, "method": method, "params": params}
        try:
            response = await self._client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "success" not in data:
                return {"success": False, "data": None, "error": "Malformed response from service"}
            return data
        except httpx.TimeoutException:
            logger.error(f"RPC timeout for {service}.{method}")
            return {"success": False, "data": None, "error": f"RPC timeout for {service}.{method}"}
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {service}.{method}: {e}")
            return {"success": False, "data": None, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"RPC call failed for {service}.{method}: {e}", exc_info=True)
            return {"success": False, "data": None, "error": f"RPC communication error: {e}"}

    async def health_check(self) -> bool:
        """Check if the target service is healthy."""
        if self._client is None:
            return False
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
