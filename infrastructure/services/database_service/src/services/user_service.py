import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, func, or_
from sqlalchemy.orm import selectinload

from database.database_manager import DatabaseManager
from models.contract import Contract, UserContract
from models.feedback import Feedback
from models.guest_parking_request import GuestParkingRequest
from models.poll_answer import PollAnswer
from models.role import Role, RolePermission
from models.service_ticket import ServiceTicket
from models.space_view import SpaceView
from models.user import User
from models.user_role import UserRole
from shared.clients.bot_client import bot_client
from shared.permissions import EVERYONE_ROLE_CODE, SUPER_ADMIN_ROLE_CODE, PermissionCodes
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

    async def _get_default_role_ids(self, *, session) -> list[int]:
        result = await session.execute(select(Role.id).where(Role.is_default == True))  # noqa: E712
        return [int(item) for item in result.scalars().all()]

    async def _serialize_user_with_links(self, *, session, user: User | None) -> dict | None:
        if user is None:
            return None
        data = Converter.to_dict(user)
        role_result = await session.execute(
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == int(user.id))
            .order_by(Role.name.asc(), Role.id.asc())
        )
        roles = list(role_result.scalars().all())
        data["roles"] = Converter.to_dict(roles)
        data["role_ids"] = [int(role.id) for role in roles]

        contract_result = await session.execute(
            select(Contract, UserContract.is_primary)
            .join(UserContract, UserContract.contract_id == Contract.id)
            .where(UserContract.user_id == int(user.id))
            .order_by(UserContract.is_primary.desc(), Contract.number.asc())
        )
        contracts = []
        primary_number = None
        for contract, is_primary in contract_result.all():
            item = Converter.to_dict(contract)
            item["is_primary"] = bool(is_primary)
            contracts.append(item)
            if primary_number is None:
                primary_number = contract.number
        data["contracts"] = contracts
        data["contract_number"] = primary_number
        return data

    @db_session_manager
    async def get_by_id(self, *, session, entity_id: Any) -> dict | None:
        user = await self.repository.get_by_id(session=session, entity_id=entity_id)
        return await self._serialize_user_with_links(session=session, user=user)

    @db_session_manager
    async def get_by_username(self, *, session, username: str):
        """Find user by username (case-insensitive). Telegram usernames are case-insensitive."""
        if not username or not username.strip():
            return None
        normalized = username.strip().lstrip("@")
        stmt = select(User).where(func.lower(User.username) == func.lower(normalized))
        result = await session.execute(stmt)
        user = result.scalars().first()
        return await self._serialize_user_with_links(session=session, user=user)

    @db_session_manager
    async def get_all(self, *, session) -> List[dict]:
        users = await self.repository.get_all(session=session)
        return [await self._serialize_user_with_links(session=session, user=user) for user in users]

    @db_session_manager
    async def get_paginated(
        self,
        *,
        session,
        page: int = 1,
        page_size: int = 10,
        sort: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        search: Optional[str] = None,
        search_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        data = await self.repository.get_paginated(
            session=session,
            page=page,
            page_size=page_size,
            sort=sort,
            filters=filters,
            search=search,
            search_columns=search_columns,
        )
        items = [
            await self._serialize_user_with_links(session=session, user=user)
            for user in data.get("items", [])
        ]
        return {"items": items, "total": data.get("total", 0)}

    async def _replace_user_roles(self, *, session, user_id: int, role_ids: list[int] | None) -> None:
        if role_ids is None:
            return
        normalized_ids = sorted({int(item) for item in role_ids})
        default_role_ids = await self._get_default_role_ids(session=session)
        normalized_ids = sorted(set(normalized_ids) | set(default_role_ids))
        if normalized_ids:
            existing = await session.execute(select(Role.id).where(Role.id.in_(normalized_ids)))
            valid_ids = {int(item) for item in existing.scalars().all()}
        else:
            valid_ids = set()
        await session.execute(delete(UserRole).where(UserRole.user_id == int(user_id)))
        for role_id in sorted(valid_ids):
            session.add(UserRole(user_id=int(user_id), role_id=role_id))

    async def _replace_primary_contract(self, *, session, user_id: int, contract_number: str | None) -> None:
        if contract_number is None:
            return
        normalized = str(contract_number or "").strip()
        await session.execute(
            delete(UserContract).where(
                UserContract.user_id == int(user_id),
                UserContract.is_primary == True,  # noqa: E712
            )
        )
        if not normalized:
            return
        contract_service = self.db_manager.services.get("contract")
        contract = await contract_service.ensure_contract(session=session, number=normalized)
        if contract is not None:
            session.add(UserContract(user_id=int(user_id), contract_id=int(contract.id), is_primary=True))

    @db_session_manager
    async def create(self, *, session, model_instance: Any, **kwargs) -> Optional[dict]:
        raw_data = dict(model_instance) if isinstance(model_instance, dict) else Converter.to_dict(model_instance)
        role_ids = raw_data.pop("role_ids", None)
        contract_number = raw_data.pop("contract_number", None)
        raw_data.pop("roles", None)
        raw_data.pop("contracts", None)
        created = await super().create(
            session=session,
            model_instance=Converter.from_dict(User, raw_data),
            **kwargs,
        )
        if created is None:
            return None
        if role_ids is None:
            role_ids = await self._get_default_role_ids(session=session)
        await self._replace_user_roles(session=session, user_id=int(created.id), role_ids=role_ids)
        await self._replace_primary_contract(session=session, user_id=int(created.id), contract_number=contract_number)
        await session.flush()
        return await self._serialize_user_with_links(session=session, user=created)

    @db_session_manager
    async def update(self, *, session, entity_id: Any, update_data: Dict[str, Any], **kwargs) -> Optional[dict]:
        update_data = dict(update_data or {})
        role_ids = update_data.pop("role_ids", None)
        contract_number = update_data.pop("contract_number", None)
        update_data.pop("roles", None)
        update_data.pop("contracts", None)
        updated = await super().update(session=session, entity_id=entity_id, update_data=update_data, **kwargs)
        if updated is None:
            return None
        await self._replace_user_roles(session=session, user_id=int(entity_id), role_ids=role_ids)
        await self._replace_primary_contract(session=session, user_id=int(entity_id), contract_number=contract_number)
        await session.flush()
        return await self._serialize_user_with_links(session=session, user=updated)

    @db_session_manager
    async def get_access_profile(self, *, session, user_id: int) -> dict:
        role_stmt = (
            select(Role)
            .outerjoin(UserRole, UserRole.role_id == Role.id)
            .where(or_(UserRole.user_id == int(user_id), Role.code == EVERYONE_ROLE_CODE, Role.is_default == True))  # noqa: E712
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.name.asc(), Role.id.asc())
        )
        role_result = await session.execute(role_stmt)
        roles = []
        seen_role_ids = set()
        permissions = set()
        for role in role_result.scalars().all():
            if role.id in seen_role_ids:
                continue
            seen_role_ids.add(role.id)
            roles.append(role)
            for role_permission in role.role_permissions or []:
                permission = role_permission.permission
                if permission is not None:
                    permissions.add(permission.code)
        is_super_admin = any(role.code == SUPER_ADMIN_ROLE_CODE for role in roles)
        return {
            "user_id": int(user_id),
            "roles": Converter.to_dict(roles),
            "permissions": sorted(permissions),
            "is_super_admin": is_super_admin,
        }

    @db_session_manager
    async def has_permission(self, *, session, user_id: int, permission_code: str) -> bool:
        access = await self.get_access_profile(session=session, user_id=user_id)
        return permission_code in set(access.get("permissions") or [])

    @db_session_manager
    async def get_by_ids(self, *, session, ids: List[int]) -> List[User]:
        """Batch-fetch users by IDs. Returns list of User (order not guaranteed)."""
        if not ids:
            return []
        users = await self.repository.get_by_ids(session=session, ids=ids)
        return [await self._serialize_user_with_links(session=session, user=user) for user in users]

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
            filters.append(
                User.id.in_(
                    select(UserRole.user_id).where(UserRole.role_id.in_(normalized_role_ids))
                )
            )
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
            .where(
                User.id.in_(
                    select(UserRole.user_id)
                    .join(Role, Role.id == UserRole.role_id)
                    .join(RolePermission, RolePermission.role_id == Role.id)
                    .join(Permission, Permission.id == RolePermission.permission_id)
                    .where(Permission.code == PermissionCodes.SERVICE_TICKETS_MANAGE)
                )
            )
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
