import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.establishments import get_owned_establishment
from app.core.deps import require_owner
from app.db.session import get_db
from app.models.user import User
from app.schemas.reports import ReportResponse
from app.services.reports import default_period, get_report

router = APIRouter(prefix="/establishments", tags=["reports"])


@router.get("/{establishment_id}/reports", response_model=ReportResponse)
def read_report(
    establishment_id: uuid.UUID,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
) -> ReportResponse:
    establishment = get_owned_establishment(establishment_id, db, current_user)

    default_from, default_to = default_period()
    from_date = from_date or default_from
    to_date = to_date or default_to

    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="'from' nao pode ser depois de 'to'"
        )

    return get_report(db, establishment.id, from_date, to_date)
