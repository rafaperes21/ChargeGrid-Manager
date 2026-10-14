import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.energy import EnergyFlowResponse, EnergySummary
from app.services.energy_flow import get_energy_flow, get_energy_summary
from app.services.reports import default_period

router = APIRouter(prefix="/establishments", tags=["energia"])


@router.get("/{establishment_id}/energy/flow", response_model=EnergyFlowResponse)
def read_energy_flow(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> EnergyFlowResponse:
    """Fluxo solar -> bateria -> carregadores <- rede: ultimo estado, serie do dia (5 min) e
    totais de hoje."""
    establishment = get_owned_establishment(establishment_id, db, current_user)
    return get_energy_flow(db, establishment)


@router.get("/{establishment_id}/energy/summary", response_model=EnergySummary)
def read_energy_summary(
    establishment_id: uuid.UUID,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> EnergySummary:
    """kWh por fonte e % renovavel no periodo (default: mes corrente)."""
    establishment = get_owned_establishment(establishment_id, db, current_user)
    default_from, default_to = default_period()
    from_date = from_date or default_from
    to_date = to_date or default_to
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="'from' nao pode ser depois de 'to'"
        )
    return get_energy_summary(db, establishment.id, from_date, to_date)
