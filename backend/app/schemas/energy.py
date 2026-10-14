from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import BatteryDispatchMode, EnergyAssetKind


class EnergyAssetOut(BaseModel):
    kind: EnergyAssetKind
    sems_serial: str
    model: str
    rated_kw: Decimal | None = None
    capacity_kwh: Decimal | None = None
    max_charge_kw: Decimal | None = None
    max_discharge_kw: Decimal | None = None
    min_soc_pct: Decimal | None = None
    dispatch_mode: BatteryDispatchMode | None = None

    model_config = {"from_attributes": True}


class BatteryModeUpdate(BaseModel):
    dispatch_mode: BatteryDispatchMode


class EnergyFlowPoint(BaseModel):
    """Potencias (kW) de um instante. `battery_kw` > 0 = descarregando, < 0 = carregando."""

    timestamp: datetime
    load_kw: Decimal
    solar_kw: Decimal
    solar_to_load_kw: Decimal
    battery_to_load_kw: Decimal
    grid_to_load_kw: Decimal
    solar_to_battery_kw: Decimal
    solar_surplus_kw: Decimal
    battery_kw: Decimal
    battery_soc_pct: Decimal | None
    grid_limit_kw: Decimal
    demand_limited_kw: Decimal


class EnergySummary(BaseModel):
    """Energia (kWh) por fonte no periodo, integrada por trapezio sobre a serie crua."""

    from_date: date
    to_date: date
    load_kwh: Decimal
    solar_generated_kwh: Decimal
    solar_to_load_kwh: Decimal
    battery_to_load_kwh: Decimal
    grid_to_load_kwh: Decimal
    solar_to_battery_kwh: Decimal
    solar_surplus_kwh: Decimal
    renewable_share_pct: Decimal | None
    peak_load_kw: Decimal
    peak_grid_kw: Decimal
    readings_count: int


class EnergyFlowResponse(BaseModel):
    inverter: EnergyAssetOut | None
    battery: EnergyAssetOut | None
    latest: EnergyFlowPoint | None
    series: list[EnergyFlowPoint]
    today: EnergySummary
