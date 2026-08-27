import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.establishment import Establishment
    from app.models.user import User


class QueueEntry(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "queue_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    establishment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("establishments.id"))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Preenchidos quando um carregador livre e oferecido a esta posicao (services/queue.py):
    # 15 min pra confirmar via RFID, senao a reserva expira e a entrada volta pro fim do
    # proprio tier (nao sai da fila). Ambos None == aguardando na fila, sem oferta ativa.
    reserved_charger_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chargers.id"), default=None
    )
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped["User"] = relationship()
    establishment: Mapped["Establishment"] = relationship()
    reserved_charger: Mapped["Charger | None"] = relationship()
