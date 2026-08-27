import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

PricingSuggestionStatus = Literal["ok", "insufficient_data"]
PricingDirection = Literal["increase", "decrease"]


class PricingSuggestionItem(BaseModel):
    day_of_week: int  # 0 = segunda, 6 = domingo (horario local)
    hour_local: int
    predicted_kwh: float
    threshold_kwh: float  # p80 (increase) ou p20 (decrease) historico daquele (dia, hora)
    direction: PricingDirection
    tariff_rule_id: uuid.UUID
    tariff_rule_name: str
    current_price_per_kwh: Decimal
    suggested_price_per_kwh: Decimal
    adjustment_pct: Decimal
    reason: str


class PricingSuggestionResponse(BaseModel):
    establishment_id: uuid.UUID
    status: PricingSuggestionStatus
    history_days_available: float
    horizon_hours: int
    max_increase_pct: Decimal
    max_decrease_pct: Decimal
    suggestions: list[PricingSuggestionItem]
