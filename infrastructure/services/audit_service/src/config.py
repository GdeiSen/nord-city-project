import os
import sys
from dataclasses import dataclass

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from shared.utils.config_base import ServiceConfig


@dataclass
class AuditServiceConfig:
    service: ServiceConfig

    @classmethod
    def from_env(cls) -> "AuditServiceConfig":
        return cls(service=ServiceConfig.from_env("audit_service", prefix="AUDIT_SERVICE_"))


def get_config() -> AuditServiceConfig:
    return AuditServiceConfig.from_env()
