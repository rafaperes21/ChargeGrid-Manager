import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ChargerModel, ChargerStatus


class ChargerDashboardItem(BaseModel):
    id: uuid.UUID
    spot_label: str
    sems_serial: str
    model: ChargerModel
    status: ChargerStatus
    nominal_power_kw: Decimal
    latest_power_kw: Decimal | None
    latest_reading_at: datetime | None


class DashboardAnomaly(BaseModel):
    charger_serial: str
    rule: str
    severity: str
    message: str


class DashboardResponse(BaseModel):
    establishment_id: uuid.UUID
    establishment_name: str
    chargers: list[ChargerDashboardItem]
    total_power_kw: Decimal
    power_limit_kw: Decimal
    power_pct: Decimal | None
    anomalies: list[DashboardAnomaly]
    ia_unavailable: bool
    revenue_today: Decimal | None
    active_sessions_count: int | None
    unavailable_reason: str
