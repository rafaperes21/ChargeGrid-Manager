import uuid
from datetime import date

from pydantic import BaseModel

from app.schemas.plan import PlanRead


class SubscriptionCreate(BaseModel):
    plan_id: uuid.UUID


class SubscriptionRead(BaseModel):
    """`plan` vem sempre montado explicitamente via `plan_to_read` (nome/preco/desconto sao
    do catalogo, nunca colunas de `Subscription`/`Plan`) - nunca `model_validate` direto em
    cima do ORM."""

    id: uuid.UUID
    plan: PlanRead
    billing_cycle_start: date
    billing_cycle_end: date | None
    active: bool
