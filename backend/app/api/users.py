import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_owner
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    for field, value in payload.model_dump(exclude_unset=True, exclude={"blocked"}).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=list[UserRead])
def list_customers(
    db: Session = Depends(get_db), current_user: User = Depends(require_owner)
) -> list[User]:
    return db.query(User).filter(User.role == UserRole.customer).all()


@router.patch("/{user_id}", response_model=UserRead)
def block_or_unblock_customer(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> User:
    customer = db.query(User).filter(User.id == user_id, User.role == UserRole.customer).first()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente nao encontrado")

    if payload.blocked is not None:
        customer.blocked = payload.blocked
    db.commit()
    db.refresh(customer)
    return customer
