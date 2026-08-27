"""Fila inteligente de espera por carregador (M3) - skill `tarifacao-e-sessoes` secao 5.

Ordenacao fixa: prioridade do plano DESC, depois ordem de chegada ASC. Nunca outro criterio
de desempate - o cliente ve a posicao em tempo real e qualquer reordenacao inexplicada vira
reclamacao (skill, secao 5). Um cliente tem no maximo uma posicao ativa na fila.

Vaga liberou -> `offer_charger` reserva o carregador por 15 min pro primeiro da fila que
ainda nao tem oferta ativa. Nao confirmou a tempo (RFID) -> `sync_queue` expira a reserva,
libera o carregador, manda a entrada pro fim do proprio tier (mesma prioridade, chegada
agora - nunca sai da fila por perder a vez) e tenta oferecer a vaga pro proximo.

`sync_queue` e o recomputo idempotente (mesmo espirito de `services/sessions.py`
`sync_session`): sem worker em background, reserva vencida so e resolvida quando alguem
consulta a fila.

Fora de escopo por ora: reserva antecipada (cliente reservar um horario futuro sem estar
na fila ao vivo, retirando aquele carregador da oferta) - item separado do milestone M3,
ainda nao modelado.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.charger import Charger
from app.models.enums import ChargerStatus, ChargingSessionStatus
from app.models.queue import QueueEntry
from app.models.session import ChargingSession
from app.models.tariff import Plan
from app.models.user import Subscription, User

RESERVATION_TIMEOUT = timedelta(minutes=15)


def _as_utc(value: datetime) -> datetime:
    """Mesma normalizacao de `services/sessions.py`: SQLite (testes) devolve naive em
    `DateTime(timezone=True)`, Postgres (prod) preserva. Assume UTC pra quem vier naive."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _resolve_queue_priority(db: Session, user_id: uuid.UUID, establishment_id: uuid.UUID) -> int:
    subscription = (
        db.query(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(
            Subscription.user_id == user_id,
            Subscription.active.is_(True),
            Plan.establishment_id == establishment_id,
        )
        .first()
    )
    if subscription is None:
        return 0  # avulso, sem assinatura ativa nesse estabelecimento
    return subscription.plan.priority


def join_queue(db: Session, user: User, establishment_id: uuid.UUID) -> QueueEntry:
    # skill tarifacao-e-sessoes secao 5: "um cliente tem no maximo uma posicao ativa na
    # fila" - sem qualificador de estabelecimento, entao o limite e global, nao por local.
    already_in_queue = (
        db.query(QueueEntry).filter(QueueEntry.user_id == user.id).first() is not None
    )
    if already_in_queue:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Usuario ja esta em uma fila"
        )

    has_open_session = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.pending, ChargingSessionStatus.active]
            ),
        )
        .first()
        is not None
    )
    if has_open_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Usuario ja tem uma sessao em andamento"
        )

    entry = QueueEntry(
        user_id=user.id,
        establishment_id=establishment_id,
        priority=_resolve_queue_priority(db, user.id, establishment_id),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # offer_charger normalmente e disparado por sessions._release_charger quando uma
    # sessao termina. Se ja existe carregador livre no momento da entrada (ninguem ficou
    # sabendo, ou a fila estava vazia ate agora), oferece na hora em vez de deixar o
    # cliente esperando um evento que nao vai acontecer tao cedo.
    livre_charger = (
        db.query(Charger)
        .filter(Charger.establishment_id == establishment_id, Charger.status == ChargerStatus.livre)
        .first()
    )
    if livre_charger is not None:
        offer_charger(db, livre_charger)
        db.refresh(entry)

    return entry


def _release_reservation(db: Session, entry: QueueEntry) -> None:
    if entry.reserved_charger_id is not None:
        charger = db.get(Charger, entry.reserved_charger_id)
        if charger is not None and charger.status == ChargerStatus.reservado:
            charger.status = ChargerStatus.livre
    entry.reserved_charger_id = None
    entry.reserved_at = None


def leave_queue(db: Session, entry: QueueEntry) -> None:
    _release_reservation(db, entry)
    db.delete(entry)
    db.commit()


def offer_charger(db: Session, charger: Charger) -> QueueEntry | None:
    """Chamar quando um carregador vira `livre` (ex.: sessao fechou em `services/sessions.py`).
    Oferece pro primeiro da fila do estabelecimento sem oferta ativa, segurando 15 min."""
    if charger.status != ChargerStatus.livre:
        return None

    candidate = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.establishment_id == charger.establishment_id,
            QueueEntry.reserved_charger_id.is_(None),
        )
        .order_by(QueueEntry.priority.desc(), QueueEntry.entered_at.asc())
        .first()
    )
    if candidate is None:
        return None

    candidate.reserved_charger_id = charger.id
    candidate.reserved_at = datetime.now(UTC)
    charger.status = ChargerStatus.reservado
    db.commit()
    db.refresh(candidate)
    return candidate


def sync_queue(db: Session, establishment_id: uuid.UUID) -> None:
    """Expira reservas de 15 min vencidas e tenta repassar a vaga liberada adiante."""
    now = datetime.now(UTC)
    reserved_entries = (
        db.query(QueueEntry)
        .filter(
            QueueEntry.establishment_id == establishment_id,
            QueueEntry.reserved_charger_id.isnot(None),
        )
        .all()
    )

    for entry in reserved_entries:
        if now - _as_utc(entry.reserved_at) < RESERVATION_TIMEOUT:
            continue

        charger_id = entry.reserved_charger_id
        _release_reservation(db, entry)
        entry.entered_at = now  # fim do proprio tier: mesma prioridade, chegada agora
        db.commit()

        charger = db.get(Charger, charger_id)
        if charger is not None:
            offer_charger(db, charger)


def get_ordered_queue(db: Session, establishment_id: uuid.UUID) -> list[QueueEntry]:
    sync_queue(db, establishment_id)
    return (
        db.query(QueueEntry)
        .filter(QueueEntry.establishment_id == establishment_id)
        .order_by(QueueEntry.priority.desc(), QueueEntry.entered_at.asc())
        .all()
    )


def find_active_reservation(
    db: Session, user_id: uuid.UUID, charger_id: uuid.UUID
) -> QueueEntry | None:
    """Usado por `services/sessions.py` `start_session` pra permitir abrir sessao num
    carregador `reservado` quando a reserva e efetivamente desse cliente e ainda nao expirou."""
    entry = (
        db.query(QueueEntry)
        .filter(QueueEntry.user_id == user_id, QueueEntry.reserved_charger_id == charger_id)
        .first()
    )
    if entry is None or entry.reserved_at is None:
        return None
    if datetime.now(UTC) - _as_utc(entry.reserved_at) >= RESERVATION_TIMEOUT:
        return None
    return entry


def consume_reservation(db: Session, entry: QueueEntry) -> None:
    """Cliente confirmou a reserva abrindo a sessao (RFID) - sai da fila."""
    db.delete(entry)
    db.commit()
