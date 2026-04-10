# ./services/base_service.py
from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, Any, Optional

from shared.constants import AuditActorType, AuditRetentionClass
from shared.utils.audit_context import derive_child_audit_context
from shared.utils.audit_events import append_business_audit_event

if TYPE_CHECKING:
    from bot import Bot

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all services"""

    def __init__(self, bot: "Bot"):
        """
        Initialize the base service.

        Args:
            bot: The bot instance, providing access to managers and other components.
        """
        self.bot = bot

    @abstractmethod
    async def initialize(self) -> None:
        """
        Asynchronously initialize the service.
        This method must be implemented in every subclass and is called upon bot startup.
        """
        pass

    def get_name(self) -> str:
        """
        Returns the service name (the class name without 'Service' in lowercase).
        e.g., 'StatsService' becomes 'stats'.
        """
        class_name = self.__class__.__name__
        if class_name.endswith('Service'):
            return class_name[:-7].lower()
        return class_name.lower()

    def derive_audit_context(
        self,
        audit_context: Optional[dict] = None,
        *,
        source_service: Optional[str] = "bot_service",
        actor_id: Any = None,
        actor_external_id: Any = None,
        actor_type: Optional[str] = None,
        actor_origin: Optional[str] = None,
        operation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        reason: Optional[str] = None,
        meta_updates: Optional[dict] = None,
    ) -> dict:
        return derive_child_audit_context(
            audit_context,
            source_service=source_service,
            actor_id=actor_id,
            actor_external_id=actor_external_id,
            actor_type=actor_type,
            actor_origin=actor_origin,
            operation_id=operation_id,
            causation_id=causation_id,
            reason=reason,
            meta_updates=meta_updates,
        )

    def build_telegram_actor_audit_context(
        self,
        *,
        telegram_user_id: Optional[int],
        audit_context: Optional[dict] = None,
        reason: Optional[str] = None,
        meta_updates: Optional[dict] = None,
    ) -> dict:
        merged_meta = dict(meta_updates or {})
        if telegram_user_id is not None:
            merged_meta.setdefault("actor_origin", "telegram")
            merged_meta.setdefault("telegram_user_id", int(telegram_user_id))
        return self.derive_audit_context(
            audit_context,
            source_service="bot_service",
            actor_id=telegram_user_id,
            actor_external_id=telegram_user_id,
            actor_type=AuditActorType.TELEGRAM_USER if telegram_user_id is not None else None,
            actor_origin="telegram" if telegram_user_id is not None else None,
            reason=reason,
            meta_updates=merged_meta,
        )

    async def append_business_audit_event(
        self,
        *,
        entity_type: str,
        entity_id: int,
        event_type: str,
        action: str,
        audit_context: Optional[dict] = None,
        event_name: Optional[str] = None,
        event_category: Optional[str] = None,
        reason: Optional[str] = None,
        meta: Optional[dict] = None,
        old_data: Optional[dict] = None,
        new_data: Optional[dict] = None,
        retention_class: str = AuditRetentionClass.OPERATIONAL,
        audit_type: str = "smart",
    ) -> None:
        try:
            await append_business_audit_event(
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                action=action,
                source_service="bot_service",
                audit_context=audit_context,
                event_name=event_name,
                event_category=event_category,
                reason=reason,
                old_data=old_data,
                new_data=new_data,
                meta=meta,
                retention_class=retention_class,
                audit_type=audit_type,
            )
        except Exception as exc:
            logger.warning(
                "Failed to append bot business audit event %s/%s for %s#%s: %s",
                event_type,
                action,
                entity_type,
                entity_id,
                exc,
            )
