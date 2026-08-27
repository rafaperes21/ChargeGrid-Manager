import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_customer, require_owner
from app.db.session import get_db
from app.models.establishment import Establishment
from app.models.queue import QueueEntry
from app.models.user import User
from app.schemas.queue import QueueEntryRead, QueueEntryWithPosition, QueueJoinRequest
from app.services.queue import get_ordered_queue, join_queue, leave_queue

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/join", response_model=QueueEntryRead, status_code=status.HTTP_201_CREATED)
def join_the_queue(
    payload: QueueJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> QueueEntry:
    establishment = db.get(Establishment, payload.establishment_id)
    if establishment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Estabelecimento nao encontrado"
        )
    return join_queue(db, current_user, payload.establishment_id)


@router.get("/mine", response_model=QueueEntryWithPosition)
def read_my_queue_position(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> QueueEntryWithPosition:
    entry = db.query(QueueEntry).filter(QueueEntry.user_id == current_user.id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao esta em nenhuma fila"
        )

    ordered = get_ordered_queue(db, entry.establishment_id)
    position = next(index for index, e in enumerate(ordered, start=1) if e.id == entry.id)

    return QueueEntryWithPosition(
        id=entry.id,
        establishment_id=entry.establishment_id,
        priority=entry.priority,
        entered_at=entry.entered_at,
        reserved_charger_id=entry.reserved_charger_id,
        reserved_at=entry.reserved_at,
        position=position,
    )


@router.delete("/mine", status_code=status.HTTP_204_NO_CONTENT)
def leave_my_queue(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> None:
    entry = db.query(QueueEntry).filter(QueueEntry.user_id == current_user.id).first()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao esta em nenhuma fila"
        )
    leave_queue(db, entry)


@router.get("", response_model=list[QueueEntryRead])
def list_queue(
    establishment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> list[QueueEntry]:
    get_owned_establishment(establishment_id, db, current_user)
    return get_ordered_queue(db, establishment_id)
