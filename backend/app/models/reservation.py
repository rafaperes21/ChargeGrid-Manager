import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReservationStatus

if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.user import User


class Reservation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Reserva antecipada de horario num carregador especifico - lacuna documentada em
    M3 ("reserva antecipada... nao modelada", skill `tarifacao-e-sessoes` secao 5).

    Diferente da reserva de 15 min da fila (`QueueEntry.reserved_charger_id`, oferecida
    quando uma vaga libera pra quem ja esta esperando ao vivo), esta e agendada pelo
    cliente com antecedencia pra um horario futuro especifico e ocupa a vaga logicamente
    nesse horario - ela nao entra na oferta da fila (`services/queue.offer_charger`
    so considera carregadores `livre`, nunca reservados por aqui).

    Tolerancia de no-show reaproveita o mesmo padrao de 15 min de `services/queue.py`
    (`RESERVATION_NO_SHOW_TOLERANCE` em `services/reservations.py`)."""

    __tablename__ = "reservations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    charger_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chargers.id"))
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, name="reservation_status"), default=ReservationStatus.pending
    )

    user: Mapped["User"] = relationship()
    charger: Mapped["Charger"] = relationship()
