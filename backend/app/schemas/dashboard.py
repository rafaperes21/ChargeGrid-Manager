import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ChargerModel, ChargerStatus
from app.schemas.session import ChargingSessionRead


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


class ChargerReadingPoint(BaseModel):
    timestamp: datetime
    power_kw: Decimal
    status: ChargerStatus


class ChargerDetailResponse(BaseModel):
    """Telemetria de um carregador individual - tela de detalhe do proprietario (nao existe
    no M4 original; adicionada como peca de venda pra GoodWe, ver M11)."""

    id: uuid.UUID
    spot_label: str
    sems_serial: str
    model: ChargerModel
    status: ChargerStatus
    nominal_power_kw: Decimal
    latest_power_kw: Decimal | None
    latest_reading_at: datetime | None
    # `None` (nunca 0%) quando nao ha nenhuma leitura na janela - o polling so acumula
    # historico desde que o ambiente subiu, "sem dado" e um estado real.
    uptime_pct: Decimal | None
    readings_window_hours: int
    power_readings: list[ChargerReadingPoint]
    recent_sessions: list[ChargingSessionRead]
    anomalies: list[DashboardAnomaly]
    ia_unavailable: bool


class DashboardResponse(BaseModel):
    establishment_id: uuid.UUID
    establishment_name: str
    chargers: list[ChargerDashboardItem]
    total_power_kw: Decimal
    power_limit_kw: Decimal
    power_pct: Decimal | None
    anomalies: list[DashboardAnomaly]
    ia_unavailable: bool
    revenue_today: Decimal
    revenue_week: Decimal
    revenue_month: Decimal
    active_sessions_count: int
