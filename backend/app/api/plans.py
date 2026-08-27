import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.tariff import Plan
from app.models.user import User
from app.schemas.plan import PlanRead, PlanUpdate
from app.services.plan_catalog import plan_to_read

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead])
def list_plans(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[PlanRead]:
    get_owned_establishment(establishment_id, db, current_user)
    plans = (
        db.query(Plan)
        .filter(Plan.establishment_id == establishment_id)
        .order_by(Plan.kind)
        .all()
    )
    return [plan_to_read(plan) for plan in plans]


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: uuid.UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> PlanRead:
    """So alterna `enabled` - o catalogo de valores e fixo (M3, Tarefa 4.1)."""
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano nao encontrado")
    get_owned_establishment(plan.establishment_id, db, current_user)

    plan.enabled = payload.enabled
    db.commit()
    db.refresh(plan)
    return plan_to_read(plan)
