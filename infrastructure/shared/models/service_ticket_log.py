from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Text, Integer, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .service_ticket import ServiceTicket
    from .user import User

class ServiceTicketLog(Base):
    __tablename__ = 'service_ticket_log' # Имя таблицы в единственном числе, как было у тебя
    id: Mapped[int] = mapped_column(Integer, Sequence('service_ticket_log_id_seq'), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('service_tickets.id', ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey('users.id', ondelete="SET NULL"))
    assignee: Mapped[Optional[str]] = mapped_column(String(200))
    msid: Mapped[Optional[int]] = mapped_column(BigInteger)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # Убираем updated_at, так как логи не должны обновляться
    
    ticket: Mapped["ServiceTicket"] = relationship(back_populates="logs")
    user: Mapped["User"] = relationship(back_populates="ticket_status_logs")