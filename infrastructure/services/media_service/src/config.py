"""
Configuration for Media Service.
Manages storage directory and HTTP server settings.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from dataclasses import dataclass
from pathlib import Path

from shared.utils.config_base import ServiceConfig, get_env_var


@dataclass
class MediaServiceConfig:
    """Complete configuration for Media Service."""

    service: ServiceConfig
    storage_dir: Path

    # Max upload size in bytes (default 25 MB for photos + short videos)
    max_upload_size: int = 25 * 1024 * 1024

    # Allowed MIME types for upload (empty = allow all; use for restrictions)
    allowed_content_types: set = None

    @classmethod
    def from_env(cls) -> "MediaServiceConfig":
        """Create configuration from environment variables."""
        # infrastructure/media_storage (from services/media_service/src/config.py)
        default_storage = Path(__file__).resolve().parents[3] / "media_storage"
        storage_str = get_env_var("MEDIA_STORAGE_DIR", default=str(default_storage))
        storage_dir = Path(storage_str).resolve()

        svc = ServiceConfig.from_env("media_service", prefix="MEDIA_SERVICE_")
        svc.port = int(get_env_var("MEDIA_SERVICE_PORT", default="8004"))
        return cls(
            service=svc,
            storage_dir=storage_dir,
            max_upload_size=int(
                get_env_var("MEDIA_MAX_UPLOAD_SIZE", default=str(25 * 1024 * 1024))
            ),
            allowed_content_types=None,  # Allow all by default; can add validation later
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        from shared.exceptions.base_exceptions import ConfigurationException

        if self.service.port < 1 or self.service.port > 65535:
            raise ConfigurationException(
                "Invalid service port", setting="MEDIA_SERVICE_PORT"
            )
        if self.max_upload_size < 1:
            raise ConfigurationException(
                "Max upload size must be positive", setting="MEDIA_MAX_UPLOAD_SIZE"
            )


def get_config() -> MediaServiceConfig:
    """Get application configuration from environment variables."""
    config = MediaServiceConfig.from_env()
    config.validate()
    return config
