from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Sequence, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .feedback import Feedback
    from .service_ticket import ServiceTicket


class ServiceTicketFeedbackRef(Base):
    __tablename__ = "service_ticket_feedback_refs"
    __table_args__ = (
        UniqueConstraint("service_ticket_id", name="uq_service_ticket_feedback_refs_service_ticket_id"),
        UniqueConstraint("feedback_id", name="uq_service_ticket_feedback_refs_feedback_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Sequence("service_ticket_feedback_refs_id_seq"), primary_key=True)
    service_ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("service_tickets.id", ondelete="CASCADE"),
    )
    feedback_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("feedbacks.id", ondelete="CASCADE"),
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    service_ticket: Mapped["ServiceTicket"] = relationship(back_populates="feedback_ref")
    feedback: Mapped["Feedback"] = relationship(back_populates="service_ticket_ref")
