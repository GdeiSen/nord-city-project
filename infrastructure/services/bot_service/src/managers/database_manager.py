# ./managers/database_manager.py
import logging
from typing import TYPE_CHECKING, Any

from .base_manager import BaseManager

if TYPE_CHECKING:
    from ..bot import Bot
    from shared.clients.database_client import DatabaseClient

logger = logging.getLogger(__name__)


class DatabaseManager(BaseManager):
    """
    Database manager that acts as a proxy to the DatabaseClient.

    After migration the client communicates with database_service over HTTP
    (HttpRpcClient) instead of RabbitMQ.  The public interface is unchanged:
    ``bot.managers.database.user``, ``bot.managers.database.service_ticket``, etc.
    """

    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.db_client: "DatabaseClient | None" = None
        self._connected: bool = False

    async def initialize(self) -> None:
        """Connect to database_service via HTTP."""
        try:
            from shared.clients.database_client import db_client as singleton_db_client

            self.db_client = singleton_db_client
            await self.db_client.connect()
            self._connected = True
            logger.info("DatabaseManager initialised and connected to database_service via HTTP.")
        except Exception as e:
            logger.error(f"Failed to initialise DatabaseManager: {e}", exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Close the HTTP connection."""
        try:
            if self.db_client and self._connected:
                await self.db_client.disconnect()
                self._connected = False
                logger.info("DatabaseManager connections cleaned up.")
        except Exception as e:
            logger.warning(f"Error during DatabaseManager cleanup: {e}", exc_info=True)

    def is_connected(self) -> bool:
        return self._connected

    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the underlying db_client."""
        if not self.db_client or not self._connected:
            raise RuntimeError("DatabaseManager is not initialised. Call initialize() first.")
        return getattr(self.db_client, name)
