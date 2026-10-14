import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import BatteryDispatchMode, EnergyAssetKind

if TYPE_CHECKING:
    from app.models.establishment import Establishment


class EnergyAsset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Inversor solar ou bateria GoodWe instalados no estabelecimento (Sprint 4, Fase 1).

    Uma tabela so para os dois tipos (em vez de duas tabelas) porque o SEMS+ trata ambos como
    "dispositivo da planta" com serial proprio; os campos que so fazem sentido para um tipo
    ficam nulos no outro. Na demo os valores sao premissas de simulacao, nao datasheet -
    `TODO(datasheet)` antes de virar orcamento entregue ao cliente.
    """

    __tablename__ = "energy_assets"

    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    kind: Mapped[EnergyAssetKind] = mapped_column(
        SAEnum(EnergyAssetKind, name="energy_asset_kind")
    )
    sems_serial: Mapped[str] = mapped_column(String(64), unique=True)
    model: Mapped[str] = mapped_column(String(80))

    # inverter: potencia de pico do arranjo FV (kWp). battery: nao usado.
    rated_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), default=None)

    # battery
    capacity_kwh: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), default=None)
    max_charge_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), default=None)
    max_discharge_kw: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), default=None)
    min_soc_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    round_trip_efficiency_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), default=None
    )
    # Politica de descarga (so faz sentido para `battery`; inversor ignora). Default =
    # autoconsumo, o comportamento original da Fase 1.
    dispatch_mode: Mapped[BatteryDispatchMode] = mapped_column(
        SAEnum(BatteryDispatchMode, name="battery_dispatch_mode"),
        default=BatteryDispatchMode.self_consumption,
        server_default=BatteryDispatchMode.self_consumption.value,
    )

    establishment: Mapped["Establishment"] = relationship()


class SiteEnergyReading(Base):
    """Fotografia do fluxo de energia do estabelecimento a cada tick do polling.

    Serie crua de potencias (kW), igual a `charger_readings`: a energia por fonte (kWh) e
    integrada por trapezio na hora de consultar (`services/energy_flow.py`), nunca agregada
    na ingestao - mesma regra da skill `integracao-sems-simulador`.

    `battery_kw` tem sinal: positivo = bateria entregando energia, negativo = carregando.
    `demand_limited_kw` e quanto o controle de demanda tirou dos carregadores neste tick
    (soma do nominal pedido - soma dos tetos aplicados).
    """

    __tablename__ = "site_energy_readings"
    __table_args__ = (
        Index(
            "ix_site_energy_readings_establishment_id_timestamp",
            "establishment_id",
            "timestamp",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    load_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    solar_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    solar_to_load_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    battery_to_load_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    grid_to_load_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    solar_to_battery_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    solar_surplus_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    battery_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    battery_soc_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    grid_limit_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    demand_limited_kw: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
