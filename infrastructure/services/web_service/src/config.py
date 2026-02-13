"""
Web Service Configuration Module.
RabbitMQ has been removed -- communication with database_service is now over HTTP.
"""

import os
import sys
from dataclasses import dataclass

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from shared.utils.config_base import ServiceConfig, get_env_var


@dataclass
class WebServiceConfig:
    """Complete configuration for Web Service."""
    service: ServiceConfig

    # Web service specific settings
    cors_origins: list
    api_prefix: str

    # Database service HTTP URL
    database_service_url: str

    # Security settings (for future auth implementation)
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_expire_minutes: int

    @classmethod
    def from_env(cls) -> "WebServiceConfig":
        """Create configuration from environment variables."""
        cors_origins_str = get_env_var("CORS_ORIGINS", default="http://localhost:3000")
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

        return cls(
            service=ServiceConfig.from_env("web_service", prefix="WEB_SERVICE_"),
            cors_origins=cors_origins,
            api_prefix=get_env_var("API_PREFIX", default="/api/v1"),
            database_service_url=get_env_var(
                "DATABASE_SERVICE_HTTP_URL", default="http://127.0.0.1:8001"
            ),
            jwt_secret_key=get_env_var("JWT_SECRET_KEY", default="your-secret-key-change-in-production"),
            jwt_algorithm=get_env_var("JWT_ALGORITHM", default="HS256"),
            jwt_expire_minutes=int(get_env_var("JWT_EXPIRE_MINUTES", default="30")),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        from shared.exceptions.base_exceptions import ConfigurationException

        if self.service.port < 1 or self.service.port > 65535:
            raise ConfigurationException("Invalid service port", setting="WEB_SERVICE_PORT")
        if not self.cors_origins:
            raise ConfigurationException("CORS origins must be specified", setting="CORS_ORIGINS")


def get_config() -> WebServiceConfig:
    """Get application configuration from environment variables."""
    config = WebServiceConfig.from_env()
    config.validate()
    return config
