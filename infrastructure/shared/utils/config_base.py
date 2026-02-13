"""
Base configuration utilities for microservices.
Provides common configuration management functionality.
RabbitMQ configuration has been removed -- services communicate via HTTP.
"""

import os
from typing import Optional, Union, List
from dataclasses import dataclass
from shared.exceptions.base_exceptions import ConfigurationException


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def url(self) -> str:
        """Get database connection URL."""
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @classmethod
    def from_env(cls, prefix: str = "DB_") -> "DatabaseConfig":
        """Create configuration from environment variables."""
        return cls(
            host=get_env_var(f"{prefix}HOST", required=True),
            port=int(get_env_var(f"{prefix}PORT", default="5432")),
            database=get_env_var(f"{prefix}NAME", required=True),
            username=get_env_var(f"{prefix}USER", required=True),
            password=get_env_var(f"{prefix}PASSWORD", required=True),
            pool_size=int(get_env_var(f"{prefix}POOL_SIZE", default="10")),
            max_overflow=int(get_env_var(f"{prefix}MAX_OVERFLOW", default="20")),
        )


@dataclass
class ServiceConfig:
    """Base service configuration."""
    name: str
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, service_name: str, prefix: str = "SERVICE_") -> "ServiceConfig":
        """Create configuration from environment variables."""
        return cls(
            name=service_name,
            host=get_env_var(f"{prefix}HOST", default="0.0.0.0"),
            port=int(get_env_var(f"{prefix}PORT", default="8000")),
            debug=get_env_var(f"{prefix}DEBUG", default="false").lower() == "true",
            log_level=get_env_var(f"{prefix}LOG_LEVEL", default="INFO").upper(),
        )


def get_env_var(
    name: str,
    default: Optional[str] = None,
    required: bool = False,
    var_type: type = str,
) -> Union[str, int, float, bool, None]:
    """
    Get environment variable with type conversion and validation.

    Args:
        name: Environment variable name.
        default: Default value if variable is not set.
        required: Whether the variable is required.
        var_type: Type to convert the value to.

    Returns:
        Environment variable value converted to specified type.

    Raises:
        ConfigurationException: If required variable is missing or conversion fails.
    """
    value = os.environ.get(name, default)

    if value is None:
        if required:
            raise ConfigurationException(
                f"Required environment variable '{name}' is not set",
                setting=name,
            )
        return None

    try:
        if var_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        else:
            return value
    except (ValueError, TypeError) as e:
        raise ConfigurationException(
            f"Invalid value for environment variable '{name}': {value}. Expected {var_type.__name__}",
            setting=name,
            details={"value": value, "expected_type": var_type.__name__, "error": str(e)},
        )


def get_env_list(
    name: str,
    default: Optional[List[str]] = None,
    separator: str = ",",
    required: bool = False,
) -> List[str]:
    """Get environment variable as a list of strings."""
    value = os.environ.get(name)

    if value is None:
        if required:
            raise ConfigurationException(
                f"Required environment variable '{name}' is not set",
                setting=name,
            )
        return default or []

    return [item.strip() for item in value.split(separator) if item.strip()]


def validate_required_env_vars(required_vars: List[str]) -> None:
    """Validate that all required environment variables are set."""
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise ConfigurationException(
            f"Required environment variables are missing: {', '.join(missing_vars)}",
            details={"missing_vars": missing_vars},
        )
