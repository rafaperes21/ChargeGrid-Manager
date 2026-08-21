import uuid
from decimal import Decimal

from pydantic import BaseModel


class EstablishmentBase(BaseModel):
    name: str
    kind: str
    phase: str
    grid_connection_kw: Decimal
    power_limit_kw: Decimal


class EstablishmentCreate(EstablishmentBase):
    pass


class EstablishmentRead(EstablishmentBase):
    id: uuid.UUID
    owner_id: uuid.UUID

    model_config = {"from_attributes": True}
