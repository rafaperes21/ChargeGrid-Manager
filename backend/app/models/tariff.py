import uuid
from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PlanKind

if TYPE_CHECKING:
    from app.models.establishment import Establishment
    from app.models.user import Subscription


class TariffRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Faixa horaria de tarifacao. Horarios em horario local do estabelecimento
    (America/Sao_Paulo) - CLAUDE.md pede cuidado nessa conversao na borda de apresentacao."""

    __tablename__ = "tariff_rules"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(100))
    days_of_week: Mapped[str] = mapped_column(String(20))  # csv "0,1,2,3,4" (0=segunda)
    start_time_local: Mapped[time] = mapped_column(Time)
    end_time_local: Mapped[time] = mapped_column(Time)
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)

    establishment: Mapped["Establishment"] = relationship(back_populates="tariff_rules")


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plans"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[PlanKind] = mapped_column(SAEnum(PlanKind, name="plan_kind"))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    free_kwh_allowance: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    priority: Mapped[int] = mapped_column(Integer, default=0)

    establishment: Mapped["Establishment"] = relationship(back_populates="plans")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")
