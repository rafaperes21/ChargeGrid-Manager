import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PlanKind


class PlanRead(BaseModel):
    """Mescla a linha do banco (`id`, `enabled`) com os valores fixos do catalogo da
    plataforma (`services/plan_catalog.plan_to_read`) - nome/preco/desconto/franquia/
    prioridade nunca vêm de input do proprietario."""

    id: uuid.UUID
    establishment_id: uuid.UUID
    kind: PlanKind
    enabled: bool
    name: str
    price: Decimal | None
    free_kwh_allowance: Decimal | None
    discount_pct: Decimal
    priority: int

    model_config = {"from_attributes": True}


class PlanUpdate(BaseModel):
    enabled: bool
