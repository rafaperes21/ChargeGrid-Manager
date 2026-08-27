from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.fleet import FleetImpactResponse, FleetOverviewResponse
from app.services.fleet import get_fleet_impact, get_fleet_overview

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.get(
    "/overview",
    response_model=FleetOverviewResponse,
    summary="Visao agregada de todos os estabelecimentos da plataforma",
    description=(
        "Painel de frota (Prioridade 5) - kWh gerenciado, receita processada e anomalias "
        "detectadas somados entre TODOS os estabelecimentos, para demonstrar escala da "
        "plataforma pra GoodWe. So numeros agregados, nunca o detalhe de um estabelecimento "
        "especifico - qualquer proprietario autenticado pode ver."
    ),
)
def read_fleet_overview(
    db: Session = Depends(get_db), current_user: User = Depends(require_owner)
) -> FleetOverviewResponse:
    return get_fleet_overview(db, settings)


@router.get(
    "/impact",
    response_model=FleetImpactResponse,
    summary="Numeros de impacto para a tela de abertura (hero, antes do login)",
    description=(
        "Subconjunto publico do overview - kWh total, CO2 evitado e receita habilitada, "
        "para a tela de impacto que aparece antes do login (Tarefa 5.3). Sem autenticacao."
    ),
)
def read_fleet_impact(db: Session = Depends(get_db)) -> FleetImpactResponse:
    return get_fleet_impact(db, settings)
