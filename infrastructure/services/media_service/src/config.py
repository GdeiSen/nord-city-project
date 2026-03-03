"""
Configuration for Storage Service.
Storage is backed by MinIO (S3-compatible object storage).
"""

import os
import sys
from urllib.parse import urlsplit

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from dataclasses import dataclass

from shared.utils.config_base import ServiceConfig, get_env_var


@dataclass
class MediaServiceConfig:
    """Complete configuration for the MinIO-backed storage service."""

    service: ServiceConfig
    max_upload_size: int
    s3_endpoint: str
    s3_public_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_secure: bool
    s3_public_secure: bool
    presigned_expiry_seconds: int
    s3_region: str | None = None
    s3_auto_create_bucket: bool = True

    @classmethod
    def from_env(cls) -> "MediaServiceConfig":
        svc = ServiceConfig.from_env("media_service", prefix="MEDIA_SERVICE_")
        svc.port = int(
            os.getenv("STORAGE_SERVICE_PORT")
            or get_env_var("MEDIA_SERVICE_PORT", default="8004")
        )

        endpoint = (
            os.getenv("STORAGE_S3_ENDPOINT")
            or os.getenv("MINIO_ENDPOINT")
            or "127.0.0.1:9000"
        ).strip()
        public_endpoint = (
            os.getenv("STORAGE_S3_PUBLIC_ENDPOINT")
            or endpoint
        ).strip()
        access_key = (
            os.getenv("STORAGE_S3_ACCESS_KEY")
            or os.getenv("MINIO_ROOT_USER")
            or "minioadmin"
        ).strip()
        secret_key = (
            os.getenv("STORAGE_S3_SECRET_KEY")
            or os.getenv("MINIO_ROOT_PASSWORD")
            or "minioadmin"
        ).strip()
        bucket = (
            os.getenv("STORAGE_S3_BUCKET")
            or "nord-city-storage"
        ).strip()
        secure_raw = (
            os.getenv("STORAGE_S3_SECURE")
            or os.getenv("MINIO_SECURE")
            or "false"
        ).strip().lower()
        auto_create_raw = (
            os.getenv("STORAGE_S3_AUTO_CREATE_BUCKET")
            or "true"
        ).strip().lower()
        region = (os.getenv("STORAGE_S3_REGION") or "").strip() or None
        parsed_endpoint = urlsplit(endpoint)
        if parsed_endpoint.scheme:
            endpoint = parsed_endpoint.netloc or parsed_endpoint.path
            if os.getenv("STORAGE_S3_SECURE") is None and os.getenv("MINIO_SECURE") is None:
                secure_raw = "true" if parsed_endpoint.scheme.lower() == "https" else "false"
        public_secure_raw = (
            os.getenv("STORAGE_S3_PUBLIC_SECURE")
            or secure_raw
        ).strip().lower()
        parsed_public_endpoint = urlsplit(public_endpoint)
        if parsed_public_endpoint.scheme:
            public_endpoint = parsed_public_endpoint.netloc or parsed_public_endpoint.path
            if os.getenv("STORAGE_S3_PUBLIC_SECURE") is None:
                public_secure_raw = "true" if parsed_public_endpoint.scheme.lower() == "https" else "false"

        return cls(
            service=svc,
            max_upload_size=int(
                os.getenv("STORAGE_MAX_UPLOAD_SIZE")
                or get_env_var("MEDIA_MAX_UPLOAD_SIZE", default=str(25 * 1024 * 1024))
            ),
            s3_endpoint=endpoint,
            s3_public_endpoint=public_endpoint,
            s3_access_key=access_key,
            s3_secret_key=secret_key,
            s3_bucket=bucket,
            s3_secure=secure_raw in {"1", "true", "yes", "on"},
            s3_public_secure=public_secure_raw in {"1", "true", "yes", "on"},
            presigned_expiry_seconds=max(
                60,
                int(os.getenv("STORAGE_S3_PRESIGNED_EXPIRY_SECONDS") or "900"),
            ),
            s3_region=region,
            s3_auto_create_bucket=auto_create_raw in {"1", "true", "yes", "on"},
        )

    def validate(self) -> None:
        from shared.exceptions.base_exceptions import ConfigurationException

        if self.service.port < 1 or self.service.port > 65535:
            raise ConfigurationException(
                "Invalid service port", setting="MEDIA_SERVICE_PORT"
            )
        if self.max_upload_size < 1:
            raise ConfigurationException(
                "Max upload size must be positive", setting="MEDIA_MAX_UPLOAD_SIZE"
            )
        if not self.s3_endpoint:
            raise ConfigurationException(
                "Missing MinIO endpoint", setting="STORAGE_S3_ENDPOINT"
            )
        if not self.s3_access_key:
            raise ConfigurationException(
                "Missing MinIO access key", setting="STORAGE_S3_ACCESS_KEY"
            )
        if not self.s3_public_endpoint:
            raise ConfigurationException(
                "Missing public MinIO endpoint", setting="STORAGE_S3_PUBLIC_ENDPOINT"
            )
        if not self.s3_secret_key:
            raise ConfigurationException(
                "Missing MinIO secret key", setting="STORAGE_S3_SECRET_KEY"
            )
        if not self.s3_bucket:
            raise ConfigurationException(
                "Missing MinIO bucket", setting="STORAGE_S3_BUCKET"
            )
        if self.presigned_expiry_seconds < 60:
            raise ConfigurationException(
                "Presigned URL expiry must be at least 60 seconds",
                setting="STORAGE_S3_PRESIGNED_EXPIRY_SECONDS",
            )


def get_config() -> MediaServiceConfig:
    config = MediaServiceConfig.from_env()
    config.validate()
    return config
