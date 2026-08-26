import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.establishment import Establishment
from app.models.user import User
from app.schemas.establishment import EstablishmentCreate, EstablishmentRead

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
