import uuid
from datetime import time
from decimal import Decimal

from pydantic import BaseModel


class TariffRuleBase(BaseModel):
    name: str
    days_of_week: str  # csv "0,1,2,3,4" (0=segunda)
    start_time_local: time
    end_time_local: time
    price_per_kwh: Decimal
    is_special: bool = False


class TariffRuleCreate(TariffRuleBase):
    establishment_id: uuid.UUID


class TariffRuleUpdate(BaseModel):
    name: str | None = None
    days_of_week: str | None = None
    start_time_local: time | None = None
    end_time_local: time | None = None
    price_per_kwh: Decimal | None = None
    is_special: bool | None = None


class TariffRuleRead(TariffRuleBase):
    id: uuid.UUID
    establishment_id: uuid.UUID

    model_config = {"from_attributes": True}
