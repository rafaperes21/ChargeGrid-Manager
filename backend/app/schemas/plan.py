import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import PlanKind


class PlanBase(BaseModel):
    name: str
    kind: PlanKind
    price: Decimal | None = None
    free_kwh_allowance: Decimal | None = None
    discount_pct: Decimal | None = None
    priority: int = 0


class PlanCreate(PlanBase):
    establishment_id: uuid.UUID


class PlanRead(PlanBase):
    id: uuid.UUID
    establishment_id: uuid.UUID

    model_config = {"from_attributes": True}
