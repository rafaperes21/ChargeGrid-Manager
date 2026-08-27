"""Reserva antecipada de horario num carregador (M10, Tarefa 2.3) - lacuna documentada em
M3 ("reserva antecipada... nao modelada", skill `tarifacao-e-sessoes` secao 5).

Igual a fila (`services/queue.py`), nao ha worker em background: `sync_reservations` e o
recomputo idempotente, so resolvido quando alguem consulta o estabelecimento (chamado pelos
mesmos pontos que ja leem status de carregador - dashboard, chargers-status, lista do dono).

Tolerancia de no-show reaproveita o mesmo valor e raciocinio da reserva de 15 min da fila
(`queue.RESERVATION_TIMEOUT`): a vaga fica logicamente ocupada (`ChargerStatus.reservado`)
a partir do horario agendado, e quem nao apareceu em ate 15 min perde a reserva e o
carregador volta a `livre`.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.charger import Charger
from app.models.enums import ChargerStatus, ReservationStatus
from app.models.reservation import Reservation
from app.models.user import User

NO_SHOW_TOLERANCE = timedelta(minutes=15)


def _as_utc(value: datetime) -> datetime:
    """Mesma normalizacao de `services/queue.py`/`services/sessions.py`: SQLite (testes)
    devolve naive em `DateTime(timezone=True)`, Postgres (prod) preserva."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def create_reservation(
    db: Session,
    user: User,
    charger_id: uuid.UUID,
    scheduled_start: datetime,
    scheduled_end: datetime,
) -> Reservation:
    charger = db.get(Charger, charger_id)
    if charger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Carregador nao encontrado"
        )

    scheduled_start = _as_utc(scheduled_start)
    scheduled_end = _as_utc(scheduled_end)
    now = datetime.now(UTC)

    if scheduled_end <= scheduled_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horario de termino deve ser depois do horario de inicio",
        )
    if scheduled_start <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horario de inicio deve ser no futuro",
        )

    overlapping = (
        db.query(Reservation)
        .filter(
            Reservation.charger_id == charger_id,
            Reservation.status == ReservationStatus.pending,
            Reservation.scheduled_start < scheduled_end,
            Reservation.scheduled_end > scheduled_start,
        )
        .first()
    )
    if overlapping is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe uma reserva para este carregador nesse horario",
        )

    reservation = Reservation(
        user_id=user.id,
        charger_id=charger_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=ReservationStatus.pending,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def sync_reservations(db: Session, establishment_id: uuid.UUID) -> None:
    """Chamado de dentro dos mesmos pontos que ja leem status de carregador do
    estabelecimento (`services/dashboard.get_chargers_status`, lista de reservas do dono) -
    mesmo espirito de `services/queue.sync_queue`."""
    now = datetime.now(UTC)
    pending = (
        db.query(Reservation)
        .join(Charger, Charger.id == Reservation.charger_id)
        .filter(
            Charger.establishment_id == establishment_id,
            Reservation.status == ReservationStatus.pending,
        )
        .all()
    )

    for reservation in pending:
        start = _as_utc(reservation.scheduled_start)
        if now < start:
            continue

        charger = db.get(Charger, reservation.charger_id)
        if now - start >= NO_SHOW_TOLERANCE:
            reservation.status = ReservationStatus.no_show
            if charger is not None and charger.status == ChargerStatus.reservado:
                charger.status = ChargerStatus.livre
            db.commit()
            continue

        # Dentro da janela [inicio, inicio + tolerancia): segura a vaga se ela ainda
        # estiver livre. Se o carregador ja estiver ocupado por outro motivo (sessao
        # avulsa, problema, offline), a reserva permanece pending - conflito de agenda
        # que o produto ainda nao resolve automaticamente (fora de escopo por ora).
        if charger is not None and charger.status == ChargerStatus.livre:
            charger.status = ChargerStatus.reservado
            db.commit()


def find_active_reservation(
    db: Session, user_id: uuid.UUID, charger_id: uuid.UUID
) -> Reservation | None:
    """Usado por `services/sessions.start_session` pra permitir abrir sessao num
    carregador `reservado` quando a reserva e deste cliente e dentro da janela de
    tolerancia de no-show - mesmo papel de `queue.find_active_reservation`."""
    now = datetime.now(UTC)
    reservation = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user_id,
            Reservation.charger_id == charger_id,
            Reservation.status == ReservationStatus.pending,
        )
        .first()
    )
    if reservation is None:
        return None
    start = _as_utc(reservation.scheduled_start)
    if now < start or now - start >= NO_SHOW_TOLERANCE:
        return None
    return reservation


def consume_reservation(db: Session, reservation: Reservation) -> None:
    """Cliente confirmou a reserva abrindo a sessao (RFID)."""
    reservation.status = ReservationStatus.fulfilled
    db.commit()


def cancel_reservation(db: Session, reservation: Reservation) -> None:
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reserva ja foi concluida, cancelada ou expirou",
        )
    charger = db.get(Charger, reservation.charger_id)
    if charger is not None and charger.status == ChargerStatus.reservado:
        charger.status = ChargerStatus.livre
    reservation.status = ReservationStatus.cancelled
    db.commit()


def get_my_reservations(db: Session, user_id: uuid.UUID) -> list[Reservation]:
    return (
        db.query(Reservation)
        .filter(Reservation.user_id == user_id)
        .order_by(Reservation.scheduled_start.desc())
        .all()
    )


def get_establishment_reservations(db: Session, establishment_id: uuid.UUID) -> list[Reservation]:
    sync_reservations(db, establishment_id)
    return (
        db.query(Reservation)
        .join(Charger, Charger.id == Reservation.charger_id)
        .filter(Charger.establishment_id == establishment_id)
        .order_by(Reservation.scheduled_start.desc())
        .all()
    )
