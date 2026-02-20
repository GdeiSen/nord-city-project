import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

from config import get_config
from models.base import Base

logger = logging.getLogger(__name__)

class Database:
    """
    Manages the PostgreSQL database connection, engine, and sessions.
    This class follows a singleton pattern, ensuring that only one instance
    manages the database resources for the application.
    """

    def __init__(self):
        """Initializes the database manager."""
        self.config = get_config().database
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """
        Initializes the database connection engine and session factory.
        It also ensures that all tables defined in the SQLAlchemy models are created.
        This method should be called once at application startup.
        """
        if self._is_initialized:
            logger.info("Database is already initialized.")
            return

        try:
            logger.info("Initializing database connection...")
            
            self.engine = create_async_engine(
                self.config.url,
                echo=get_config().enable_sql_logging,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True
            )

            # Create the session factory
            self.session_factory = sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create all tables defined in Base's metadata
            async with self.engine.begin() as conn:
                logger.info("Creating database tables...")
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully.")

            self._is_initialized = True
            logger.info("Database initialization completed successfully.")

        except Exception as e:
            logger.critical(f"Database initialization failed: {e}", exc_info=True)
            raise ConnectionError(f"Could not initialize database: {e}")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provides a database session as an asynchronous context manager.
        It ensures the session is properly closed after use.
        Transaction management (commit/rollback) is handled by the caller.

        Yields:
            An active SQLAlchemy AsyncSession.
        
        Raises:
            ConnectionError: If the database has not been initialized.
        """
        if not self._is_initialized or not self.session_factory:
            raise ConnectionError("Database is not initialized. Call initialize() first.")
        
        session: AsyncSession = self.session_factory()
        try:
            yield session
        finally:
            await session.close()

    async def close(self) -> None:
        """Closes the database engine's connection pool."""
        if self.engine:
            await self.engine.dispose()
            self._is_initialized = False
            logger.info("Database connection pool disposed.")

    async def health_check(self) -> bool:
        """
        Performs a simple query to check the database connection health.
        
        Returns:
            True if the connection is healthy, False otherwise.
        """
        if not self._is_initialized:
            return False
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# --- Singleton Instance ---
# This ensures that the entire application uses the same database connection manager.
_db_instance: Optional[Database] = None

def get_database() -> Database:
    """
    Returns the singleton instance of the Database manager.
    
    Returns:
        The single Database instance for the application.
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance