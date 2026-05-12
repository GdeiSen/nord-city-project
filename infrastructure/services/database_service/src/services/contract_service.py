from sqlalchemy import select

from models.contract import Contract
from .base_service import BaseService, db_session_manager


class ContractService(BaseService):
    model_class = Contract

    @db_session_manager
    async def get_by_number(self, *, session, number: str) -> Contract | None:
        normalized = str(number or "").strip()
        if not normalized:
            return None
        result = await session.execute(select(Contract).where(Contract.number == normalized))
        return result.scalars().first()

    @db_session_manager
    async def ensure_contract(self, *, session, number: str, title: str | None = None) -> Contract | None:
        normalized = str(number or "").strip()
        if not normalized:
            return None
        existing = await self.get_by_number(session=session, number=normalized)
        if existing:
            return existing
        contract = Contract(number=normalized, title=title or None, status="ACTIVE")
        return await self.repository.create(session=session, obj_in=contract)
