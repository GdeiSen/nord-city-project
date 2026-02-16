"""
Configuration for Bot Service.
RabbitMQ has been removed -- communication with database_service is now over HTTP.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from dataclasses import dataclass
from shared.utils.config_base import ServiceConfig, get_env_var


@dataclass
class BotServiceConfig:
    """Complete configuration for Bot Service."""
    service: ServiceConfig

    # Bot-specific settings
    bot_token: str
    admin_chat_id: str
    chief_engineer_chat_id: str

    # Database service HTTP URL
    database_service_url: str

    @classmethod
    def from_env(cls) -> "BotServiceConfig":
        """Create configuration from environment variables."""
        return cls(
            service=ServiceConfig.from_env("bot_service"),
            bot_token=get_env_var("BOT_TOKEN", required=True),
            admin_chat_id=get_env_var("ADMIN_CHAT_ID", default=""),
            chief_engineer_chat_id=get_env_var("CHIEF_ENGINEER_CHAT_ID", default=""),
            database_service_url=get_env_var(
                "DATABASE_SERVICE_HTTP_URL", default="http://127.0.0.1:8001"
            ),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        from shared.exceptions.base_exceptions import ConfigurationException

        if self.service.port < 1 or self.service.port > 65535:
            raise ConfigurationException("Invalid service port", setting="SERVICE_PORT")
        if not self.bot_token:
            raise ConfigurationException("Bot token is required", setting="BOT_TOKEN")


# Global configuration instance
config: BotServiceConfig = None


def get_config() -> BotServiceConfig:
    """Get global configuration instance."""
    global config
    if config is None:
        config = BotServiceConfig.from_env()
        config.validate()
    return config
