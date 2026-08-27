import uuid
from decimal import Decimal

from pydantic import BaseModel


class EstablishmentBase(BaseModel):
    name: str
    kind: str
    phase: str
    grid_connection_kw: Decimal
    power_limit_kw: Decimal
    max_increase_pct: Decimal = Decimal("20.00")
    max_decrease_pct: Decimal = Decimal("20.00")


class EstablishmentCreate(EstablishmentBase):
    pass


class EstablishmentUpdate(BaseModel):
    max_increase_pct: Decimal | None = None
    max_decrease_pct: Decimal | None = None


class EstablishmentRead(EstablishmentBase):
    id: uuid.UUID
    owner_id: uuid.UUID

    model_config = {"from_attributes": True}
