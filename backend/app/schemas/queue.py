import uuid
from datetime import datetime

from pydantic import BaseModel


class QueueJoinRequest(BaseModel):
    establishment_id: uuid.UUID


class QueueEntryRead(BaseModel):
    id: uuid.UUID
    establishment_id: uuid.UUID
    priority: int
    entered_at: datetime
    reserved_charger_id: uuid.UUID | None
    reserved_at: datetime | None

    model_config = {"from_attributes": True}


class QueueEntryWithPosition(QueueEntryRead):
    position: int


class QueueEntryOwnerRead(QueueEntryRead):
    """So para `GET /queue` (dono) - nome do cliente, pra ele saber quem chamar. `/queue/mine`
    (cliente) nao precisa disso, e' o proprio nome dele."""

    user_full_name: str
