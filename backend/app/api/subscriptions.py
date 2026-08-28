import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_customer
from app.db.session import get_db
from app.models.user import Subscription, User
from app.schemas.subscription import SubscriptionCreate, SubscriptionRead
from app.services.plan_catalog import plan_to_read
from app.services.subscriptions import get_active_subscription, subscribe

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _to_read(subscription: Subscription) -> SubscriptionRead:
    return SubscriptionRead(
        id=subscription.id,
        plan=plan_to_read(subscription.plan),
        billing_cycle_start=subscription.billing_cycle_start,
        billing_cycle_end=subscription.billing_cycle_end,
        active=subscription.active,
    )


@router.get("/me", response_model=SubscriptionRead | None)
def read_my_subscription(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> SubscriptionRead | None:
    subscription = get_active_subscription(db, current_user.id, establishment_id)
    return _to_read(subscription) if subscription is not None else None


@router.post("", response_model=SubscriptionRead | None)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> SubscriptionRead | None:
    """Devolve `None` quando o cliente escolhe `avulso` - nao existe linha de assinatura pra
    esse nivel (ver `services/subscriptions.subscribe`)."""
    subscription = subscribe(db, current_user, payload.plan_id)
    return _to_read(subscription) if subscription is not None else None
