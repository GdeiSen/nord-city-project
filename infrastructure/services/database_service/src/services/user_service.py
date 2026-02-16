from sqlalchemy import select, func
from database.database_manager import DatabaseManager
from shared.models.user import User
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