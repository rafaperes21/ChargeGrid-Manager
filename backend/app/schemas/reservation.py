import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ReservationStatus


class ReservationCreate(BaseModel):
    charger_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime


class ReservationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    charger_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime
    status: ReservationStatus

    model_config = {"from_attributes": True}


class ReservationOwnerRead(ReservationRead):
    """So para `GET /establishments/{id}/reservations` (dono) - nome do cliente e vaga,
    pra ele conseguir cruzar com quem chega no local."""

    user_full_name: str
    spot_label: str
