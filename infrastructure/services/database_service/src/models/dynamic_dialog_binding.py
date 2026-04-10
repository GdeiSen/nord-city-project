from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Sequence, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .feedback import Feedback
    from .poll_answer import PollAnswer
    from .service_ticket import ServiceTicket


class DynamicDialogBinding(Base):
    __tablename__ = "dynamic_dialog_bindings"

    id: Mapped[int] = mapped_column(
        Integer,
        Sequence("dynamic_dialog_bindings_id_seq"),
        primary_key=True,
        server_default=text("nextval('dynamic_dialog_bindings_id_seq'::regclass)"),
    )
    ddid: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    dialog_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="ddid_binding")
    poll_answers: Mapped[list["PollAnswer"]] = relationship(back_populates="ddid_binding")
    service_tickets: Mapped[list["ServiceTicket"]] = relationship(back_populates="ddid_binding")

    __table_args__ = (
        UniqueConstraint("dialog_id", "sequence_id", "item_id", name="uq_dynamic_dialog_bindings_parts"),
    )
