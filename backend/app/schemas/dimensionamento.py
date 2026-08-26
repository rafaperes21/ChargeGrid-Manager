from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import ChargerModel

EstablishmentType = Literal["shopping", "estacionamento", "empresa"]
Phase = Literal["monofasico", "trifasico"]


class DimensionamentoRequest(BaseModel):
    establishment_type: EstablishmentType
    parking_spots: int
    available_power_kw: Decimal
    phase: Phase


class BudgetEstimate(BaseModel):
    capex: Decimal | None
    payback_months: Decimal | None
    note: str | None


class DimensionamentoResponse(BaseModel):
    recommended_model: ChargerModel
    recommended_model_nominal_power_kw: Decimal
    recommended_model_max_current_a: Decimal
    max_chargers: int
    min_power_required_kw: Decimal | None
    budget: BudgetEstimate
