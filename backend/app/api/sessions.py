import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import get_current_user, require_customer, require_owner
from app.db.session import get_db
from app.models.enums import ChargingSessionStatus
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.schemas.session import (
    ChargingSessionRead,
    CurrentSessionRead,
    ReceiptRead,
    SessionPaymentMethodUpdate,
    SessionStartRequest,
)
from app.services.dashboard import latest_reading
from app.services.sessions import (
    build_receipt,
    estimate_live_amount,
    set_payment_method,
    start_session,
    sync_session,
)
from app.services.vehicle_battery import estimate_battery_status

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=ChargingSessionRead, status_code=status.HTTP_201_CREATED)
def start_charging_session(
    payload: SessionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> ChargingSession:
    return start_session(db, current_user, payload.charger_id)


@router.get("/current", response_model=CurrentSessionRead)
def read_current_session(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> CurrentSessionRead:
    session = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == current_user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.pending, ChargingSessionStatus.active]
            ),
        )
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma sessao em andamento"
        )
    session = sync_session(db, session)

    if session.status not in (ChargingSessionStatus.pending, ChargingSessionStatus.active):
        # sync_session pode fechar a sessao (finished/error) nesta mesma chamada - o
        # contrato deste endpoint e sempre "pending/active, ou 404", nunca vazar um status
        # terminal so porque a transicao aconteceu neste poll especifico. Quem quiser o
        # resultado fechado usa GET /sessions/{id}/receipt.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma sessao em andamento"
        )

    estimated_amount_due = None
    battery_pct_estimate = None
    estimated_minutes_remaining = None
    if session.status == ChargingSessionStatus.active:
        estimated_amount_due = estimate_live_amount(db, session, datetime.now(tz=UTC))
        reading = latest_reading(db, session.charger_id)
        battery_pct_estimate, estimated_minutes_remaining = estimate_battery_status(
            vehicle_model=current_user.vehicle_model,
            energy_kwh=session.energy_kwh,
            current_power_kw=reading.power_kw if reading else None,
        )

    return CurrentSessionRead(
        **ChargingSessionRead.model_validate(session).model_dump(),
        estimated_amount_due=estimated_amount_due,
        battery_pct_estimate=battery_pct_estimate,
        estimated_minutes_remaining=estimated_minutes_remaining,
    )


@router.patch("/current/payment-method", response_model=ChargingSessionRead)
def update_current_session_payment_method(
    payload: SessionPaymentMethodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> ChargingSession:
    """Declarativo (Tarefa 4.3) - o cliente escolhe entre as formas que o estabelecimento
    aceita enquanto a sessao ainda esta pending/active. Nao valida contra
    `accepted_payment_methods` do estabelecimento: essa lista e so o que a tela do cliente
    oferece pra escolher, nao uma trava de backend (a UI ja restringe as opcoes)."""
    session = (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == current_user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.pending, ChargingSessionStatus.active]
            ),
        )
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma sessao em andamento"
        )
    return set_payment_method(db, session, payload.payment_method)


@router.get("/mine", response_model=list[ChargingSessionRead])
def list_my_sessions(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> list[ChargingSession]:
    """Historico do cliente - so sessoes terminais (finished/error); pending/active ja
    aparecem em `GET /sessions/current`."""
    return (
        db.query(ChargingSession)
        .filter(
            ChargingSession.user_id == current_user.id,
            ChargingSession.status.in_(
                [ChargingSessionStatus.finished, ChargingSessionStatus.error]
            ),
        )
        .order_by(ChargingSession.started_at.desc())
        .all()
    )


@router.get("/{session_id}/receipt", response_model=ReceiptRead)
def read_session_receipt(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    session = db.get(ChargingSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")

    is_session_owner = session.user_id == current_user.id
    is_establishment_owner = (
        db.query(Establishment)
        .filter(
            Establishment.id == session.establishment_id,
            Establishment.owner_id == current_user.id,
        )
        .first()
        is not None
    )
    if not is_session_owner and not is_establishment_owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")

    try:
        return build_receipt(session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[ChargingSessionRead])
def list_sessions(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[ChargingSession]:
    get_owned_establishment(establishment_id, db, current_user)

    return (
        db.query(ChargingSession)
        .filter(ChargingSession.establishment_id == establishment_id)
        .order_by(ChargingSession.started_at.desc())
        .all()
    )
