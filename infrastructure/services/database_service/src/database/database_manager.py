import logging
from .connection import get_database, Database
from .repository_manager import RepositoryManager
from .service_manager import ServiceManager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    A centralized manager that integrates database connections, repositories,
    and services. This class acts as the main orchestrator for all
    database-related resources, providing a single point of access.
    """
    def __init__(self):
        """
        Initializes the DatabaseManager by creating instances of the
        database connection handler, RepositoryManager, and ServiceManager.
        """
        self.db_connection: Database = get_database()
        self.repositories = RepositoryManager()
        self.services = ServiceManager()
        logger.info("DatabaseManager initialized with connection, repository, and service managers.")

    async def initialize_db(self):
        """
        Initializes the database connection and creates all tables.
        This should be called once when the application starts.
        """
        await self.db_connection.initialize()
        logger.info("Database connection initialized and tables created.")

    def get_session(self):
        """
        Provides a new asynchronous database session.
        This is intended to be used as a context manager.

        Returns:
            An async session context manager.
        """
        return self.db_connection.get_session()