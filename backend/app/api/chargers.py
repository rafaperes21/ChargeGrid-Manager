import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.charger import Charger
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
    current_user: User = Depends(require_owner),
) -> list[Charger]:
    get_owned_establishment(establishment_id, db, current_user)
    return db.query(Charger).filter(Charger.establishment_id == establishment_id).all()
