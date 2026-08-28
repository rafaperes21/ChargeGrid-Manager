import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.establishment import Establishment
from app.models.user import User
from app.schemas.dashboard import ChargerDashboardItem
from app.schemas.establishment import EstablishmentCreate, EstablishmentRead, EstablishmentUpdate
from app.schemas.plan import PlanRead
from app.schemas.reservation import ReservationOwnerRead, ReservationRead
from app.services.dashboard import get_chargers_status
from app.services.plan_catalog import plan_to_read, provision_plans_for_establishment
from app.services.reservations import get_establishment_reservations
from app.services.subscriptions import list_enabled_plans

router = APIRouter(prefix="/establishments", tags=["establishments"])


@router.get("", response_model=list[EstablishmentRead])
def list_all_establishments(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Establishment]:
    """Lista todos os estabelecimentos - usado pelo portal do cliente para descobrir onde
    carregar. Sem filtro por dono (diferente de `/establishments/me`): nome/tipo de
    estabelecimento nao e dado sensivel, e o cliente ainda nao tem uma forma melhor
    (geolocalizacao/QR code) de descobrir o estabelecimento onde esta - fora de escopo por
    enquanto."""
    return db.query(Establishment).all()


@router.post("", response_model=EstablishmentRead, status_code=status.HTTP_201_CREATED)
def create_establishment(
    payload: EstablishmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> Establishment:
    establishment = Establishment(**payload.model_dump(), owner_id=current_user.id)
    db.add(establishment)
    db.commit()
    db.refresh(establishment)
    provision_plans_for_establishment(db, establishment.id)
    return establishment


@router.get("/me", response_model=list[EstablishmentRead])
def list_my_establishments(
    db: Session = Depends(get_db), current_user: User = Depends(require_owner)
) -> list[Establishment]:
    return db.query(Establishment).filter(Establishment.owner_id == current_user.id).all()


def get_owned_establishment(
    establishment_id: uuid.UUID, db: Session, current_user: User
) -> Establishment:
    """Carrega o estabelecimento garantindo que pertence ao owner autenticado.

    404 (nao 403) para nao revelar a um owner que um id de outro estabelecimento existe."""
    establishment = (
        db.query(Establishment)
        .filter(Establishment.id == establishment_id, Establishment.owner_id == current_user.id)
        .first()
    )
    if establishment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Estabelecimento nao encontrado"
        )
    return establishment


@router.get("/{establishment_id}", response_model=EstablishmentRead)
def get_establishment(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> Establishment:
    return get_owned_establishment(establishment_id, db, current_user)


@router.get("/{establishment_id}/chargers-status", response_model=list[ChargerDashboardItem])
def get_establishment_chargers_status(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChargerDashboardItem]:
    """Status somente-leitura de cada carregador - usado na tela de detalhe do
    estabelecimento no mapa do cliente (Tarefa 2.2 do M10). Aberto a qualquer usuario
    autenticado, mesmo raciocinio de `GET /chargers`: status de carregador nao e dado
    financeiro/sensivel."""
    establishment = db.get(Establishment, establishment_id)
    if establishment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Estabelecimento nao encontrado"
        )
    return get_chargers_status(db, establishment_id)


@router.get("/{establishment_id}/plans", response_model=list[PlanRead])
def list_establishment_plans(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PlanRead]:
    """Planos habilitados deste estabelecimento, visivel a qualquer cliente autenticado -
    mesmo raciocinio de `/chargers-status` (nao e dado financeiro sensivel, o catalogo de
    valores ja e publico/fixo). So os habilitados - o cliente nunca ve um nivel que o
    proprietario decidiu nao oferecer (o `/plans` do proprietario devolve todos, este nao)."""
    establishment = db.get(Establishment, establishment_id)
    if establishment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Estabelecimento nao encontrado"
        )
    return [plan_to_read(plan) for plan in list_enabled_plans(db, establishment_id)]


@router.get("/{establishment_id}/reservations", response_model=list[ReservationOwnerRead])
def list_establishment_reservations(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[ReservationOwnerRead]:
    """Agenda de reservas antecipadas do estabelecimento (Tarefa 2.3 do M10) - pro dono
    conseguir cruzar com quem chega no local."""
    get_owned_establishment(establishment_id, db, current_user)
    entries = get_establishment_reservations(db, establishment_id)
    return [
        ReservationOwnerRead(
            **ReservationRead.model_validate(entry).model_dump(),
            user_full_name=entry.user.full_name,
            spot_label=entry.charger.spot_label,
        )
        for entry in entries
    ]


@router.patch("/{establishment_id}", response_model=EstablishmentRead)
def update_establishment(
    establishment_id: uuid.UUID,
    payload: EstablishmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> Establishment:
    """Hoje so os limites da sugestao de precificacao (M8) sao editaveis por aqui - os
    demais campos (potencia, fase) dependem de re-dimensionamento, fora de escopo."""
    establishment = get_owned_establishment(establishment_id, db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(establishment, field, value)
    db.commit()
    db.refresh(establishment)
    return establishment
