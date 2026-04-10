from database.database_manager import DatabaseManager
from models.dynamic_dialog_binding import DynamicDialogBinding
from shared.utils.ddid_utils import normalize_ddid, parse_ddid

from .base_service import BaseService, db_session_manager

DDID_PLACEHOLDER = "0000-0000-0000"


class DynamicDialogBindingService(BaseService):
    """Registry of canonical DDID bindings used by domain entities."""

    model_class = DynamicDialogBinding

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_ddid(self, *, session, ddid: str) -> DynamicDialogBinding | None:
        normalized = normalize_ddid(str(ddid or "").strip() or DDID_PLACEHOLDER)
        results = await self.repository.find(session=session, ddid=normalized)
        return results[0] if results else None

    @db_session_manager
    async def ensure_binding(self, *, session, ddid: str) -> DynamicDialogBinding:
        normalized = normalize_ddid(str(ddid or "").strip() or DDID_PLACEHOLDER)
        existing = await self.get_by_ddid(session=session, ddid=normalized)
        if existing is not None:
            return existing

        dialog_id, sequence_id, item_id = parse_ddid(normalized)
        binding = DynamicDialogBinding(
            ddid=normalized,
            dialog_id=dialog_id,
            sequence_id=sequence_id,
            item_id=item_id,
        )
        return await self.repository.create(session=session, obj_in=binding)
