from decimal import Decimal

from fastapi import APIRouter, Depends

from app.core.deps import require_owner
from app.models.user import User
from app.schemas.dimensionamento import (
    BudgetEstimate,
    DimensionamentoRequest,
    DimensionamentoResponse,
)
from app.services import dimensionamento
from app.services.charger_catalog import CHARGER_SPECS

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_TARIFA_ASSUMIDA_PARA_PAYBACK = Decimal("1.20")  # so usada se unit_price existir - hoje sempre None


@router.post("/dimensionamento", response_model=DimensionamentoResponse)
def calcular_dimensionamento(
    payload: DimensionamentoRequest, current_user: User = Depends(require_owner)
) -> DimensionamentoResponse:
    model = dimensionamento.select_model(payload.phase, payload.available_power_kw)
    qty = dimensionamento.max_chargers(
        payload.available_power_kw, model, payload.establishment_type, payload.parking_spots
    )

    min_power = None
    if qty == 0:
        min_power = dimensionamento.min_power_required_kw(model, payload.establishment_type)

    budget = dimensionamento.estimate_budget(
        model, max(qty, 1), payload.establishment_type, _TARIFA_ASSUMIDA_PARA_PAYBACK
    )

    return DimensionamentoResponse(
        recommended_model=model,
        recommended_model_nominal_power_kw=CHARGER_SPECS[model].nominal_power_kw,
        recommended_model_max_current_a=CHARGER_SPECS[model].max_current_a,
        max_chargers=qty,
        min_power_required_kw=min_power,
        budget=BudgetEstimate(**budget),
    )
