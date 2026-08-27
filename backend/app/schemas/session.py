import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ChargingSessionStatus


class SessionStartRequest(BaseModel):
    charger_id: uuid.UUID


class ChargingSessionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    charger_id: uuid.UUID
    establishment_id: uuid.UUID
    status: ChargingSessionStatus
    started_at: datetime
    ended_at: datetime | None
    energy_kwh: Decimal | None
    amount_due: Decimal | None
    tariff_rate_applied: Decimal | None
    plan_discount_pct: Decimal | None
    free_minutes_applied: int | None

    model_config = {"from_attributes": True}


class CurrentSessionRead(ChargingSessionRead):
    """So usado por `GET /sessions/current` - `estimated_amount_due` e uma projecao ao vivo
    (tarifa+plano resolvidos como se a sessao fechasse agora), nunca o valor final."""

    estimated_amount_due: Decimal | None


class ReceiptRead(BaseModel):
    session_id: str
    started_at: str
    ended_at: str | None
    energy_kwh: str
    tariff_rate_applied: str
    plan_discount_pct: str
    free_minutes_applied: int | None
    amount_due: str
    gross_amount: str
    promo_value: str
    discount_value: str
    franquia_value: str
    final_amount: str
