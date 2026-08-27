import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import require_customer
from app.db.session import get_db
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationRead
from app.services.reservations import cancel_reservation, create_reservation, get_my_reservations

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create_my_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> Reservation:
    return create_reservation(
        db, current_user, payload.charger_id, payload.scheduled_start, payload.scheduled_end
    )


@router.get("/mine", response_model=list[ReservationRead])
def list_my_reservations(
    db: Session = Depends(get_db), current_user: User = Depends(require_customer)
) -> list[Reservation]:
    return get_my_reservations(db, current_user.id)


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_reservation(
    reservation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
) -> None:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None or reservation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reserva nao encontrada"
        )
    cancel_reservation(db, reservation)
