import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.tariff import TariffRule
from app.models.user import User
from app.schemas.tariff import TariffRuleCreate, TariffRuleRead, TariffRuleUpdate
from app.services.tariffs import validate_no_overlap

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


def _get_owned_tariff_rule(
    tariff_rule_id: uuid.UUID, db: Session, current_user: User
) -> TariffRule:
    rule = db.query(TariffRule).filter(TariffRule.id == tariff_rule_id).first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarifa nao encontrada")
    get_owned_establishment(rule.establishment_id, db, current_user)
    return rule


@router.post("", response_model=TariffRuleRead, status_code=status.HTTP_201_CREATED)
def create_tariff_rule(
    payload: TariffRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> TariffRule:
    get_owned_establishment(payload.establishment_id, db, current_user)
    validate_no_overlap(
        db,
        payload.establishment_id,
        payload.days_of_week,
        payload.start_time_local,
        payload.end_time_local,
    )

    rule = TariffRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=list[TariffRuleRead])
def list_tariff_rules(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[TariffRule]:
    get_owned_establishment(establishment_id, db, current_user)
    return db.query(TariffRule).filter(TariffRule.establishment_id == establishment_id).all()


@router.patch("/{tariff_rule_id}", response_model=TariffRuleRead)
def update_tariff_rule(
    tariff_rule_id: uuid.UUID,
    payload: TariffRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> TariffRule:
    rule = _get_owned_tariff_rule(tariff_rule_id, db, current_user)

    updates = payload.model_dump(exclude_unset=True)
    days_of_week = updates.get("days_of_week", rule.days_of_week)
    start_time_local = updates.get("start_time_local", rule.start_time_local)
    end_time_local = updates.get("end_time_local", rule.end_time_local)
    validate_no_overlap(
        db,
        rule.establishment_id,
        days_of_week,
        start_time_local,
        end_time_local,
        exclude_id=rule.id,
    )

    for field, value in updates.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{tariff_rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tariff_rule(
    tariff_rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> None:
    rule = _get_owned_tariff_rule(tariff_rule_id, db, current_user)
    db.delete(rule)
    db.commit()
