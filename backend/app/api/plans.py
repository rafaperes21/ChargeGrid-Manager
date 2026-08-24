import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.tariff import Plan
from app.models.user import User
from app.schemas.plan import PlanCreate, PlanRead

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> Plan:
    get_owned_establishment(payload.establishment_id, db, current_user)

    plan = Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[PlanRead])
def list_plans(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[Plan]:
    get_owned_establishment(establishment_id, db, current_user)
    return db.query(Plan).filter(Plan.establishment_id == establishment_id).all()
