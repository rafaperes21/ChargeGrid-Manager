import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import get_current_user, require_customer, require_owner
from app.db.session import get_db
from app.models.enums import ChargingSessionStatus
from app.models.establishment import Establishment
from app.models.session import ChargingSession
from app.models.user import User
from app.schemas.session import ChargingSessionRead, ReceiptRead, SessionStartRequest
from app.services.sessions import build_receipt, start_session, sync_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=ChargingSessionRead, status_code=status.HTTP_201_CREATED)
def start_charging_session(
    payload: SessionStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> ChargingSession:
    return start_session(db, current_user, payload.charger_id)


@router.get("/current", response_model=ChargingSessionRead)
def read_current_session(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> ChargingSession:
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
    return sync_session(db, session)


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
