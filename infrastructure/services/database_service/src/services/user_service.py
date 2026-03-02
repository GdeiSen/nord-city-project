from typing import List
from sqlalchemy import select, func, or_
from database.database_manager import DatabaseManager
from models.user import User
from .base_service import BaseService, db_session_manager


class UserService(BaseService):
    """Service for user-related business logic."""
    model_class = User

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
