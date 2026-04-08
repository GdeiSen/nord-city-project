from typing import Optional

from database.database_manager import DatabaseManager
from models.feedback import Feedback
from models.service_ticket import ServiceTicket
from models.service_ticket_feedback_ref import ServiceTicketFeedbackRef
from shared.constants import FeedbackTypes

from .base_service import BaseService, db_session_manager


class FeedbackService(BaseService):
    """
    Service for feedback-related business logic.

    Besides generic CRUD, it owns the domain workflow for binding a feedback
    record to a completed service ticket via ``service_ticket_feedback_refs``.
    """

    model_class = Feedback

    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager)

    @db_session_manager
    async def get_by_service_ticket_id(
        self,
        *,
        session,
        service_ticket_id: int,
    ) -> Optional[Feedback]:
        ref_service = self.db_manager.services.get("service_ticket_feedback_ref")
        ref = await ref_service.get_by_service_ticket_id(
            session=session,
            service_ticket_id=int(service_ticket_id),
        )
        if ref is None:
            return None
        return await self.repository.get_by_id(session=session, entity_id=int(ref.feedback_id))

    @db_session_manager
    async def upsert_service_ticket_feedback(
        self,
        *,
        session,
        service_ticket_id: int,
        user_id: int,
        ddid: str,
        answer: str,
        text: str | None = None,
        feedback_type: str = FeedbackTypes.SERVICE_TICKET,
        _audit_context: dict | None = None,
    ) -> Feedback:
        ticket_repo = self.db_manager.repositories.get(ServiceTicket)
        ticket = await ticket_repo.get_by_id(session=session, entity_id=int(service_ticket_id))
        if ticket is None:
            raise ValueError(f"Service ticket {service_ticket_id} not found")

        normalized_payload = {
            "user_id": int(user_id),
            "ddid": str(ddid or "").strip(),
            "feedback_type": str(feedback_type or FeedbackTypes.SERVICE_TICKET),
            "answer": str(answer or "").strip(),
            "text": str(text).strip() if text is not None and str(text).strip() else None,
        }
        if not normalized_payload["ddid"]:
            raise ValueError("ddid is required for service ticket feedback")
        if not normalized_payload["answer"]:
            raise ValueError("answer is required for service ticket feedback")

        ref_service = self.db_manager.services.get("service_ticket_feedback_ref")
        existing_ref = await ref_service.get_by_service_ticket_id(
            session=session,
            service_ticket_id=int(service_ticket_id),
        )

        if existing_ref is not None:
            existing_feedback = await self.repository.get_by_id(
                session=session,
                entity_id=int(existing_ref.feedback_id),
            )
            if existing_feedback is not None:
                updated = await self.update(
                    session=session,
                    entity_id=int(existing_feedback.id),
                    update_data=normalized_payload,
                    _audit_context=_audit_context,
                )
                if updated is None:
                    raise RuntimeError(
                        f"Failed to update feedback {existing_feedback.id} for ticket {service_ticket_id}"
                    )
                return updated

        created = await self.create(
            session=session,
            model_instance=Feedback(**normalized_payload),
            _audit_context=_audit_context,
        )
        if created is None or created.id is None:
            raise RuntimeError(f"Failed to create feedback for ticket {service_ticket_id}")

        if existing_ref is None:
            await ref_service.create(
                session=session,
                model_instance=ServiceTicketFeedbackRef(
                    service_ticket_id=int(service_ticket_id),
                    feedback_id=int(created.id),
                ),
            )
        else:
            await ref_service.update(
                session=session,
                entity_id=int(existing_ref.id),
                update_data={"feedback_id": int(created.id)},
            )

        return created
