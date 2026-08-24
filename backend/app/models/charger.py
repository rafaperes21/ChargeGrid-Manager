import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ChargerModel, ChargerStatus

if TYPE_CHECKING:
    from app.models.establishment import Establishment

# Instancia unica reaproveitada nas duas tabelas abaixo para o Postgres nao tentar
# criar o tipo ENUM `charger_status` duas vezes na migration autogerada.
charger_status_type = SAEnum(ChargerStatus, name="charger_status")


class Charger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chargers"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    sems_serial: Mapped[str] = mapped_column(String(64), unique=True)
    model: Mapped[ChargerModel] = mapped_column(SAEnum(ChargerModel, name="charger_model"))
    spot_label: Mapped[str] = mapped_column(String(30))
    status: Mapped[ChargerStatus] = mapped_column(
        charger_status_type, default=ChargerStatus.offline
    )
    nominal_power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))

    establishment: Mapped["Establishment"] = relationship(back_populates="chargers")
    readings: Mapped[list["ChargerReading"]] = relationship(back_populates="charger")


class ChargerReading(Base):
    """Serie temporal do polling do SEMS+. PK inteira (nao UUID): volume alto, sem necessidade
    de opacidade de id, e chave sequencial e mais barata para o indice principal."""

    __tablename__ = "charger_readings"
    __table_args__ = (Index("ix_charger_readings_charger_id_timestamp", "charger_id", "timestamp"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    status: Mapped[ChargerStatus] = mapped_column(charger_status_type)

    charger: Mapped["Charger"] = relationship(back_populates="readings")
