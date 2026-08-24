import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ChargerModel, ChargerStatus


class ChargerBase(BaseModel):
    sems_serial: str
    model: ChargerModel
    spot_label: str
    nominal_power_kw: Decimal


class ChargerCreate(ChargerBase):
    establishment_id: uuid.UUID


class ChargerRead(ChargerBase):
    id: uuid.UUID
    establishment_id: uuid.UUID
    status: ChargerStatus

    model_config = {"from_attributes": True}
