import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

AnomalyRule = Literal[
    "zero_power_connected", "over_nominal_power", "offline_prolonged", "energy_regression"
]
AnomalySeverity = Literal["high", "medium"]


class AnomalyEvidence(BaseModel):
    timestamp: datetime
    power_kw: Decimal
    status: str
    total_energy_kwh: Decimal
    error_code: str | None = None


class AnomalyAlert(BaseModel):
    charger_id: uuid.UUID
    charger_serial: str
    establishment_id: uuid.UUID
    rule: AnomalyRule
    severity: AnomalySeverity
    message: str
    window_start: datetime
    window_end: datetime
    evidence: list[AnomalyEvidence]


class AnomalyReport(BaseModel):
    establishment_id: uuid.UUID
    generated_at: datetime
    lookback_hours: int
    alerts: list[AnomalyAlert]
