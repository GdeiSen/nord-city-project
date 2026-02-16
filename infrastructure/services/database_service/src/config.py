"""
Configuration for Database Service.
Manages database connection and HTTP server settings.
RabbitMQ has been removed -- the service now exposes a FastAPI HTTP server.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from dataclasses import dataclass
from shared.utils.config_base import DatabaseConfig, ServiceConfig, get_env_var


@dataclass
class DatabaseServiceConfig:
    """
    Complete configuration for Database Service.
    """
    service: ServiceConfig
    database: DatabaseConfig

    # Service-specific settings
    enable_sql_logging: bool = False
    connection_timeout: int = 30

    @classmethod
    def from_env(cls) -> "DatabaseServiceConfig":
        """Create configuration from environment variables."""
        return cls(
            service=ServiceConfig.from_env("database_service"),
            database=DatabaseConfig.from_env(),
            enable_sql_logging=get_env_var("ENABLE_SQL_LOGGING", default="false").lower() == "true",
            connection_timeout=int(get_env_var("CONNECTION_TIMEOUT", default="30")),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        from shared.exceptions.base_exceptions import ConfigurationException

        if self.service.port < 1 or self.service.port > 65535:
            raise ConfigurationException("Invalid service port", setting="SERVICE_PORT")
        if self.database.pool_size < 1:
            raise ConfigurationException("Database pool size must be positive", setting="DB_POOL_SIZE")
        if self.connection_timeout < 1:
            raise ConfigurationException("Connection timeout must be positive", setting="CONNECTION_TIMEOUT")


# Global configuration instance
config: DatabaseServiceConfig = None


def get_config() -> DatabaseServiceConfig:
    """Get global configuration (lazy-initialised from env vars)."""
    global config
    if config is None:
        config = DatabaseServiceConfig.from_env()
        config.validate()
    return config
