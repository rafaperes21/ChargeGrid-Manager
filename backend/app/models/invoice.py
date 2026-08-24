import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import Company


class Invoice(Base, UUIDPrimaryKeyMixin):
    """Fatura corporativa consolidada. Imutavel por convencao de aplicacao: nunca fazer
    UPDATE apos emitida, apenas gerar uma nova se precisar corrigir."""

    __tablename__ = "invoices"

    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship()
