from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Sequence, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .user import User


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, Sequence("contracts_id_seq"), primary_key=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user_contracts: Mapped[List["UserContract"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
    )


class UserContract(Base):
    __tablename__ = "user_contracts"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="user_contracts")
    contract: Mapped["Contract"] = relationship(back_populates="user_contracts")

    __table_args__ = (
        UniqueConstraint("user_id", "contract_id", name="uq_user_contracts_user_contract"),
    )
