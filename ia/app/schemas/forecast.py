import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ForecastStatus = Literal["ok", "insufficient_data"]


class HeatmapCell(BaseModel):
    day_of_week: int  # 0 = segunda, 6 = domingo (horario local)
    hour_local: int
    predicted_kwh: float
    lower: float
    upper: float


class PeriodMetric(BaseModel):
    mae: float
    mape: float | None  # None quando a janela de CV tem horas de demanda real ~0 (MAPE indefinido)


class BacktestSummary(BaseModel):
    overall_mae: float
    overall_mape: float | None
    by_period: dict[str, PeriodMetric]


class ForecastResponse(BaseModel):
    establishment_id: uuid.UUID
    status: ForecastStatus
    model_version: str | None
    trained_at: datetime | None
    history_days_available: float
    horizon_hours: int
    heatmap: list[HeatmapCell]
    peak_labels: list[str]
    backtest: BacktestSummary | None
    fallback_used: bool
    fallback_reason: str | None
