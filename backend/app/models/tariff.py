import uuid
from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Time, UniqueConstraint
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
    """Uma linha por nivel do catalogo fixo (`services/plan_catalog.PLAN_CATALOG`) por
    estabelecimento - nome/preco/desconto/franquia/prioridade vêm do catalogo, nunca deste
    modelo (M3, Tarefa 4.1: proprietario so escolhe `enabled`, nunca os valores)."""

    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("establishment_id", "kind", name="uq_plans_establishment_kind"),
    )

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    kind: Mapped[PlanKind] = mapped_column(SAEnum(PlanKind, name="plan_kind"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    establishment: Mapped["Establishment"] = relationship(back_populates="plans")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")
