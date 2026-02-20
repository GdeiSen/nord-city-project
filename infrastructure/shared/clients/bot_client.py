"""
BotClient -- typed proxy for bot_service over HTTP.

Uses HttpRpcClient under the hood. Provides explicit service proxies
for invoking bot-side operations from other services (e.g. web_service).

Architecture follows the same proxy pattern as DatabaseClient:
    web_service  →  BotClient (HTTP RPC)  →  bot_service internal endpoint
"""

import os
import logging
from typing import Dict, Any

from shared.clients.http_rpc_client import HttpRpcClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service proxies
# ---------------------------------------------------------------------------

class _BotServiceProxy:
    """
    Base proxy for calling bot service methods via HTTP RPC.
    """

    def __init__(self, client: HttpRpcClient, service_name: str):
        self._client = client
        self._service = service_name

    async def _call(self, method: str, **params) -> Dict[str, Any]:
        """Execute an RPC call to the bot service."""
        return await self._client.call(self._service, method, params)


class _TelegramAuthProxy(_BotServiceProxy):
    """Proxy for the TelegramAuthService in bot_service."""

    async def send_otp_code(self, *, user_id: int) -> Dict[str, Any]:
        """Request the bot to send an OTP code to the specified user."""
        return await self._call("send_otp_code", user_id=user_id)


class _NotificationProxy(_BotServiceProxy):
    """Proxy for the NotificationService in bot_service."""

    async def notify_new_ticket(self, *, ticket_id: int) -> Dict[str, Any]:
        """Notify admin chat about a new service ticket."""
        return await self._call("notify_new_ticket", ticket_id=ticket_id)

    async def edit_ticket_message(self, *, ticket_id: int) -> Dict[str, Any]:
        """Edit the ticket message in admin chat with current data. Call when ticket is edited via website."""
        return await self._call("edit_ticket_message", ticket_id=ticket_id)

    async def delete_ticket_messages(self, *, ticket_id: int) -> Dict[str, Any]:
        """Delete ticket message and all replies from admin chat. Call before deleting ticket from DB."""
        return await self._call("delete_ticket_messages", ticket_id=ticket_id)

    async def notify_ticket_completion(self, *, ticket_id: int) -> Dict[str, Any]:
        """Notify user about ticket completion. Bot sends message and deletes reply messages in admin chat."""
        return await self._call("notify_ticket_completion", ticket_id=ticket_id)

    async def notify_new_guest_parking(self, *, req_id: int) -> Dict[str, Any]:
        """Отправить заявку на гостевую парковку в чат администраторов (при создании с сайта)."""
        return await self._call("notify_new_guest_parking", req_id=req_id)

    async def edit_guest_parking_message(self, *, req_id: int) -> Dict[str, Any]:
        """Отредактировать сообщение заявки в чате администраторов (при изменении с сайта)."""
        return await self._call("edit_guest_parking_message", req_id=req_id)

    async def delete_guest_parking_messages(self, *, req_id: int) -> Dict[str, Any]:
        """Удалить сообщение заявки из чата администраторов (перед удалением из БД)."""
        return await self._call("delete_guest_parking_messages", req_id=req_id)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class BotClient:
    """
    Singleton client for bot_service.
    Connects via HTTP (HttpRpcClient) and exposes typed service proxies.
    """

    _instance: "BotClient | None" = None
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return

        base_url = os.getenv("BOT_SERVICE_HTTP_URL", "http://127.0.0.1:8002")
        timeout = float(os.getenv("BOT_SERVICE_TIMEOUT", "30"))

        self._http = HttpRpcClient(base_url, timeout=timeout)
        self._connected = False

        # --- Explicit service proxies ---
        self.telegram_auth = _TelegramAuthProxy(self._http, "telegram_auth")
        self.notification = _NotificationProxy(self._http, "notification")

        self._is_initialized = True

    async def connect(self):
        """Open the HTTP connection to bot_service."""
        if self._connected:
            return
        try:
            await self._http.connect()
            self._connected = True
            logger.info("BotClient connected to bot_service via HTTP.")
        except Exception as e:
            logger.error(f"Failed to connect BotClient: {e}", exc_info=True)
            self._connected = False
            raise

    async def disconnect(self):
        """Close the HTTP connection."""
        if self._connected:
            await self._http.disconnect()
            self._connected = False
            logger.info("BotClient disconnected.")


# Singleton instance for easy import
bot_client = BotClient()
