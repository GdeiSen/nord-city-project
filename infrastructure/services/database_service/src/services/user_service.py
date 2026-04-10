import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, or_

from database.database_manager import DatabaseManager
from models.feedback import Feedback
from models.guest_parking_request import GuestParkingRequest
from models.poll_answer import PollAnswer
from models.service_ticket import ServiceTicket
from models.space_view import SpaceView
from models.user import User
from shared.clients.bot_client import bot_client
from shared.constants import Roles
from shared.utils.converter import Converter

from .base_service import BaseService, db_session_manager

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for user-related business logic."""
    model_class = User
    _CASCADE_AUDIT_TARGETS = (
        ("service_ticket", ServiceTicket, "ServiceTicket"),
        ("feedback", Feedback, "Feedback"),
        ("poll", PollAnswer, "PollAnswer"),
        ("guest_parking", GuestParkingRequest, "GuestParkingRequest"),
        ("space_view", SpaceView, "SpaceView"),
    )

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_username(self, *, session, username: str):
        """Find user by username (case-insensitive). Telegram usernames are case-insensitive."""
        if not username or not username.strip():
            return None
        normalized = username.strip().lstrip("@")
        stmt = select(User).where(func.lower(User.username) == func.lower(normalized))
        result = await session.execute(stmt)
        return result.scalars().first()

    @db_session_manager
    async def get_by_ids(self, *, session, ids: List[int]) -> List[User]:
        """Batch-fetch users by IDs. Returns list of User (order not guaranteed)."""
        if not ids:
            return []
        return await self.repository.get_by_ids(session=session, ids=ids)

    @db_session_manager
    async def get_notification_recipients(
        self,
        *,
        session,
        role_ids: List[int] | None = None,
        user_ids: List[int] | None = None,
    ) -> List[User]:
        """Resolve a deduplicated recipient list by selected roles and explicit user IDs."""
        normalized_role_ids = sorted({int(role_id) for role_id in (role_ids or [])})
        normalized_user_ids = sorted({int(user_id) for user_id in (user_ids or [])})
        if not normalized_role_ids and not normalized_user_ids:
            return []

        stmt = select(User)
        filters = []
        if normalized_role_ids:
            filters.append(User.role.in_(normalized_role_ids))
        if normalized_user_ids:
            filters.append(User.id.in_(normalized_user_ids))

        stmt = stmt.where(or_(*filters)).order_by(
            func.lower(func.coalesce(User.last_name, "")),
            func.lower(func.coalesce(User.first_name, "")),
            User.id.asc(),
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @db_session_manager
    async def get_managers_for_object(self, *, session, object_id: int) -> List[User]:
        stmt = (
            select(User)
            .where(User.object_id == int(object_id))
            .where(User.role == Roles.MANAGER)
            .order_by(User.last_name.asc(), User.first_name.asc(), User.id.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _collect_cascade_snapshots(self, *, session, user_id: int) -> Dict[str, List[dict]]:
        snapshots: Dict[str, List[dict]] = {}
        for _, model_class, entity_type in self._CASCADE_AUDIT_TARGETS:
            repo = self.db_manager.repositories.get(model_class)
            entities = await repo.find(session=session, user_id=user_id)
            if entities:
                snapshots[entity_type] = [Converter.to_dict(item) for item in entities]
        return snapshots

    @staticmethod
    def _build_cascade_audit_context(
        audit_context: Optional[dict],
        *,
        root_user_id: int,
    ) -> dict:
        context = dict(audit_context or {})
        meta = context.get("meta") if isinstance(context.get("meta"), dict) else {}
        meta = dict(meta)
        meta.update(
            {
                "cascade": True,
                "cascade_root": "User",
                "cascade_root_id": int(root_user_id),
            }
        )
        context["meta"] = meta
        context.setdefault("reason", "cascade_delete_from_user")
        return context

    async def _write_cascade_audit_entries(
        self,
        *,
        session,
        root_user_id: int,
        snapshots: Dict[str, List[dict]],
        audit_context: Optional[dict],
    ) -> None:
        if not snapshots:
            return

        cascade_context = self._build_cascade_audit_context(
            audit_context,
            root_user_id=root_user_id,
        )
        for service_name, _, entity_type in self._CASCADE_AUDIT_TARGETS:
            entries = snapshots.get(entity_type, [])
            if not entries:
                continue
            service = self.db_manager.services.get(service_name)
            for entry in entries:
                entity_id = entry.get("id")
                if entity_id is None:
                    continue
                await service._write_audit(
                    session=session,
                    entity_id=int(entity_id),
                    action="delete",
                    old_data=entry,
                    new_data=None,
                    audit_context=cascade_context,
                )

    async def _notify_admins_about_user_deletion(
        self,
        *,
        user_data: dict,
        snapshots: Dict[str, List[dict]],
    ) -> None:
        counts = {
            "service_tickets": len(snapshots.get("ServiceTicket", [])),
            "feedbacks": len(snapshots.get("Feedback", [])),
            "poll_answers": len(snapshots.get("PollAnswer", [])),
            "guest_parking_requests": len(snapshots.get("GuestParkingRequest", [])),
            "space_views": len(snapshots.get("SpaceView", [])),
        }
        ticket_ids = sorted(
            int(item["id"])
            for item in snapshots.get("ServiceTicket", [])
            if item.get("id") is not None
        )

        try:
            await bot_client.notification.notify_user_deleted(
                user_id=int(user_data["id"]),
                username=user_data.get("username"),
                full_name=" ".join(
                    part for part in [
                        str(user_data.get("last_name") or "").strip(),
                        str(user_data.get("first_name") or "").strip(),
                        str(user_data.get("middle_name") or "").strip(),
                    ] if part
                ).strip(),
                cascade_counts=counts,
                service_ticket_ids=ticket_ids,
            )
        except Exception as exc:
            logger.warning(
                "Failed to notify admins about user cascade deletion (user_id=%s): %s",
                user_data.get("id"),
                exc,
            )

    @db_session_manager
    async def delete(self, *, session, entity_id: Any, **kwargs) -> bool:
        existing_user = await self.repository.get_by_id(session=session, entity_id=entity_id)
        if existing_user is None:
            return False

        audit_context = kwargs.get("_audit_context")
        user_data = Converter.to_dict(existing_user)
        cascade_snapshots = await self._collect_cascade_snapshots(session=session, user_id=int(entity_id))

        deleted = await super().delete(session=session, entity_id=entity_id, **kwargs)
        if not deleted:
            return False

        await self._write_cascade_audit_entries(
            session=session,
            root_user_id=int(entity_id),
            snapshots=cascade_snapshots,
            audit_context=audit_context,
        )
        await self._notify_admins_about_user_deletion(
            user_data=user_data,
            snapshots=cascade_snapshots,
        )
        return True
