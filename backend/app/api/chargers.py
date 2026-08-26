import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.charger import Charger
from app.models.establishment import Establishment
from app.models.user import User
from app.schemas.charger import ChargerCreate, ChargerRead

router = APIRouter(prefix="/chargers", tags=["chargers"])


@router.post("", response_model=ChargerRead, status_code=status.HTTP_201_CREATED)
def create_charger(
    payload: ChargerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> Charger:
    get_owned_establishment(payload.establishment_id, db, current_user)

    charger = Charger(**payload.model_dump())
    db.add(charger)
    db.commit()
    db.refresh(charger)
    return charger


@router.get("", response_model=list[ChargerRead])
def list_chargers(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Charger]:
    """Aberto pra qualquer usuario autenticado (owner ou customer), nao so o dono - o
    portal do cliente precisa disso pro mapa de disponibilidade. Status de carregador nao e
    dado financeiro/sensivel, diferente das rotas de tarifa/receita (essas continuam
    owner-only via `get_owned_establishment`)."""
    establishment = db.get(Establishment, establishment_id)
    if establishment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Estabelecimento nao encontrado"
        )
    return db.query(Charger).filter(Charger.establishment_id == establishment_id).all()
