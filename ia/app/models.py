"""Modelos SQLAlchemy proprios do servico de IA - le as mesmas tabelas do Postgres do
backend (`backend/app/models/`), mas com um `Base`/metadata independente, ja que `ia` e
`backend` sao dois servicos deployados separadamente. So mapeia as colunas que a IA
efetivamente usa. Nunca escreve nestas tabelas - ver `app/db/session.py`."""

import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Time
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.enums import ChargerModel, ChargerStatus


class Base(DeclarativeBase):
    pass


class Establishment(Base):
    __tablename__ = "establishments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    kind: Mapped[str] = mapped_column(String(30))
    max_increase_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    max_decrease_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    chargers: Mapped[list["Charger"]] = relationship(back_populates="establishment")
    tariff_rules: Mapped[list["TariffRule"]] = relationship(back_populates="establishment")


class Charger(Base):
    __tablename__ = "chargers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    sems_serial: Mapped[str] = mapped_column(String(64))
    model: Mapped[ChargerModel] = mapped_column(SAEnum(ChargerModel, name="charger_model"))
    nominal_power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    status: Mapped[ChargerStatus] = mapped_column(SAEnum(ChargerStatus, name="charger_status"))

    establishment: Mapped["Establishment"] = relationship(back_populates="chargers")
    readings: Mapped[list["ChargerReading"]] = relationship(back_populates="charger")


class TariffRule(Base):
    """So os campos que a regra de precificacao sugerida (secao 2 da skill) precisa pra
    achar a faixa vigente num (dia da semana, hora local) - mesma logica de
    `backend/app/services/tariffs.py`, duplicada aqui de proposito (servico read-only,
    deployado separado, nunca importa codigo do backend)."""

    __tablename__ = "tariff_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    name: Mapped[str] = mapped_column(String(100))
    days_of_week: Mapped[str] = mapped_column(String(20))
    start_time_local: Mapped[time] = mapped_column(Time)
    end_time_local: Mapped[time] = mapped_column(Time)
    price_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)

    establishment: Mapped["Establishment"] = relationship(back_populates="tariff_rules")


class ChargerReading(Base):
    __tablename__ = "charger_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    power_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    status: Mapped[ChargerStatus] = mapped_column(SAEnum(ChargerStatus, name="charger_status"))
    total_energy_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    error_code: Mapped[str | None] = mapped_column(String(50), default=None)

    charger: Mapped["Charger"] = relationship(back_populates="readings")
