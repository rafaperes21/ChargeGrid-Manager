import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DailyRevenuePoint(BaseModel):
    date: date
    revenue: Decimal


class ReportResponse(BaseModel):
    establishment_id: uuid.UUID
    from_date: date
    to_date: date
    revenue_total: Decimal
    completed_sessions_count: int
    average_ticket: Decimal | None
    total_energy_kwh: Decimal
    daily_revenue: list[DailyRevenuePoint]


class ChargerOccupancy(BaseModel):
    """Uma linha por vaga - base do grafico 'ocupacao por vaga' (visao de mercado: qual
    vaga rende mais), sempre a partir de sessoes `finished` reais, nunca estimado."""

    charger_id: uuid.UUID
    spot_label: str
    sessions_count: int
    energy_kwh: Decimal
    revenue: Decimal
    hours_charged: Decimal


class OccupancyResponse(BaseModel):
    establishment_id: uuid.UUID
    from_date: date
    to_date: date
    chargers: list[ChargerOccupancy]
