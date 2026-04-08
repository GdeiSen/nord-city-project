from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Sequence, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from shared.constants import FeedbackTypes

if TYPE_CHECKING:
    from .dynamic_dialog_binding import DynamicDialogBinding
    from .service_ticket_feedback_ref import ServiceTicketFeedbackRef
    from .user import User


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(Integer, Sequence("feedbacks_id_seq"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    ddid: Mapped[str] = mapped_column(String(14), ForeignKey("dynamic_dialog_bindings.ddid"))
    feedback_type: Mapped[str] = mapped_column(String(50), default=FeedbackTypes.GENERAL)
    answer: Mapped[str] = mapped_column(String(2000))
    text: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="feedbacks")
    ddid_binding: Mapped["DynamicDialogBinding"] = relationship(back_populates="feedbacks")
    service_ticket_ref: Mapped[Optional["ServiceTicketFeedbackRef"]] = relationship(
        back_populates="feedback",
        cascade="all, delete-orphan",
        uselist=False,
    )
