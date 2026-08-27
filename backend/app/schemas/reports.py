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
