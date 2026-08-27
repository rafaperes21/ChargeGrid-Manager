import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

PricingSuggestionStatus = Literal["ok", "insufficient_data", "ia_unavailable"]


class PricingSuggestionItem(BaseModel):
    day_of_week: int
    hour_local: int
    predicted_kwh: float
    threshold_kwh: float
    direction: Literal["increase", "decrease"]
    tariff_rule_id: uuid.UUID
    tariff_rule_name: str
    current_price_per_kwh: Decimal
    suggested_price_per_kwh: Decimal
    adjustment_pct: Decimal
    reason: str


class PricingSuggestionsResponse(BaseModel):
    establishment_id: uuid.UUID
    status: PricingSuggestionStatus
    suggestions: list[PricingSuggestionItem]
