import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChargingSessionStatus, PaymentMethod

if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.establishment import Establishment
    from app.models.user import User


class ChargingSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "charging_sessions"
    __table_args__ = (
        Index("ix_charging_sessions_user_id_started_at", "user_id", "started_at"),
        Index("ix_charging_sessions_establishment_id_started_at", "establishment_id", "started_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id"))
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))

    status: Mapped[ChargingSessionStatus] = mapped_column(
        SAEnum(ChargingSessionStatus, name="charging_session_status"),
        default=ChargingSessionStatus.pending,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    energy_kwh: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    amount_due: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    # Snapshot da tarifa no momento da sessao - nunca reprocessar contra tariff_rules atual,
    # senao o extrato de meses passados deixa de bater (ver M1, armadilha 1).
    tariff_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tariff_rules.id", ondelete="SET NULL")
    )
    tariff_rate_applied: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    plan_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    free_minutes_applied: Mapped[int | None] = mapped_column(Integer)

    # Declarativo (M3, Tarefa 4.3): registra o que o cliente escolheu, nunca processa
    # pagamento de verdade - mesmo espirito do snapshot de tarifa, sem gateway/PCI/latencia.
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method"), default=None
    )

    user: Mapped["User"] = relationship()
    charger: Mapped["Charger"] = relationship()
    establishment: Mapped["Establishment"] = relationship()
